from __future__ import annotations

from pathlib import Path
from typing import Any

from groq import Groq

from yt_dlp_subs.srt import SubtitleSegment


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

    with audio_path.open("rb") as audio_file:
        response = client.audio.transcriptions.create(
            file=(audio_path.name, audio_file.read()),
            **kwargs,
        )

    return segments_from_response(response)


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

