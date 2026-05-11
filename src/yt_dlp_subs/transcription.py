from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from groq import Groq

from yt_dlp_subs.srt import SubtitleSegment

MAX_DIRECT_UPLOAD_BYTES = 24 * 1024 * 1024
GROQ_AUDIO_RATE = "16000"
GROQ_AUDIO_CHANNELS = "1"
GROQ_AUDIO_BITRATE = "48k"
CHUNK_SECONDS = 10 * 60
CHUNK_OVERLAP_SECONDS = 5


def transcribe_audio(
    audio_path: Path,
    *,
    api_key: str,
    model: str = "whisper-large-v3-turbo",
    language: str | None = None,
    prompt: str | None = None,
    temperature: float = 0.0,
) -> list[SubtitleSegment]:
    client = Groq(api_key=api_key)
    with TemporaryDirectory(prefix="yt-dlp-subs-groq-") as temp_dir:
        prepared_path = Path(temp_dir) / "audio.mp3"
        prepare_audio_for_groq(audio_path, prepared_path)

        kwargs = _transcription_kwargs(
            model=model,
            language=language,
            prompt=prompt,
            temperature=temperature,
        )

        if prepared_path.stat().st_size <= MAX_DIRECT_UPLOAD_BYTES:
            return _transcribe_prepared_audio(client, prepared_path, kwargs)

        return _transcribe_chunked_audio(client, prepared_path, Path(temp_dir), kwargs)


def prepare_audio_for_groq(source_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-map",
        "0:a:0",
        "-ar",
        GROQ_AUDIO_RATE,
        "-ac",
        GROQ_AUDIO_CHANNELS,
        "-c:a",
        "libmp3lame",
        "-b:a",
        GROQ_AUDIO_BITRATE,
        str(output_path),
    ]
    _run_media_command(command, f"ffmpeg could not prepare audio for Groq from {source_path}")


def _transcription_kwargs(
    *,
    model: str,
    language: str | None,
    prompt: str | None,
    temperature: float,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "response_format": "verbose_json",
        "timestamp_granularities": ["segment"],
        "temperature": temperature,
    }
    if language:
        kwargs["language"] = language
    if prompt:
        kwargs["prompt"] = prompt
    return kwargs


def _transcribe_prepared_audio(
    client: Groq,
    audio_path: Path,
    kwargs: dict[str, Any],
) -> list[SubtitleSegment]:
    with audio_path.open("rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=(audio_path.name, audio_file.read()),
            **kwargs,
        )

    return segments_from_response(response)


def _transcribe_chunked_audio(
    client: Groq,
    audio_path: Path,
    temp_path: Path,
    kwargs: dict[str, Any],
) -> list[SubtitleSegment]:
    duration = _audio_duration_seconds(audio_path)
    segments: list[SubtitleSegment] = []
    start = 0.0
    index = 0

    while start < duration:
        chunk_duration = min(CHUNK_SECONDS + CHUNK_OVERLAP_SECONDS, duration - start)
        chunk_path = temp_path / f"chunk-{index:04d}.mp3"
        _write_audio_chunk(audio_path, chunk_path, start=start, duration=chunk_duration)
        if chunk_path.stat().st_size > MAX_DIRECT_UPLOAD_BYTES:
            raise RuntimeError(
                f"audio chunk {chunk_path.name} is still larger than Groq's "
                f"{MAX_DIRECT_UPLOAD_BYTES // (1024 * 1024)}MB upload limit"
            )

        chunk_segments = _transcribe_prepared_audio(client, chunk_path, kwargs)
        if index > 0:
            chunk_segments = [
                segment
                for segment in chunk_segments
                if segment.start >= CHUNK_OVERLAP_SECONDS
            ]
        segments.extend(_offset_segments(chunk_segments, start))

        index += 1
        start += CHUNK_SECONDS

    return _dedupe_overlapping_segments(segments)


def _write_audio_chunk(
    source_path: Path,
    output_path: Path,
    *,
    start: float,
    duration: float,
) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(source_path),
        "-vn",
        "-ar",
        GROQ_AUDIO_RATE,
        "-ac",
        GROQ_AUDIO_CHANNELS,
        "-c:a",
        "libmp3lame",
        "-b:a",
        GROQ_AUDIO_BITRATE,
        str(output_path),
    ]
    _run_media_command(command, f"ffmpeg could not split audio chunk at {start:.3f}s")


def _audio_duration_seconds(audio_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        message = f"ffprobe could not read audio duration from {audio_path}"
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message) from exc

    try:
        duration = float(result.stdout.decode(errors="replace").strip())
    except ValueError as exc:
        raise RuntimeError(f"ffprobe returned an invalid audio duration for {audio_path}") from exc

    if duration <= 0:
        raise RuntimeError(f"ffprobe returned a non-positive audio duration for {audio_path}")
    return duration


def _run_media_command(command: list[str], failure_message: str) -> None:
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        message = failure_message
        if detail:
            message = f"{message}: {detail}"
        raise RuntimeError(message) from exc

    output_path = Path(command[-1])
    if not output_path.exists():
        raise RuntimeError(f"ffmpeg completed but did not produce {output_path}")


def _offset_segments(segments: list[SubtitleSegment], offset: float) -> list[SubtitleSegment]:
    return [
        SubtitleSegment(
            start=segment.start + offset,
            end=segment.end + offset,
            text=segment.text,
        )
        for segment in segments
    ]


def _dedupe_overlapping_segments(segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
    deduped: list[SubtitleSegment] = []
    seen: set[tuple[int, str]] = set()
    for segment in segments:
        key = (round(segment.start), segment.text.strip().casefold())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(segment)
    return deduped


def segments_from_response(response: Any) -> list[SubtitleSegment]:
    raw_segments = _get_value(response, "segments")
    if raw_segments:
        segments = [
            SubtitleSegment(
                start=float(_get_value(segment, "start", 0.0)),
                end=float(_get_value(segment, "end", 0.0)),
                text=str(_get_value(segment, "text", "")),
            )
            for segment in raw_segments
        ]
        return [segment for segment in segments if segment.text.strip()]

    text = str(_get_value(response, "text", "")).strip()
    if text:
        return [SubtitleSegment(start=0.0, end=1.0, text=text)]
    return []


def _get_value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)
