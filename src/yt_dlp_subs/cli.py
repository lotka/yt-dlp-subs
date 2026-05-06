from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from groq import GroqError

from yt_dlp_subs.downloader import DownloadFailure, download_audio, output_stem_from_title
from yt_dlp_subs.srt import to_srt
from yt_dlp_subs.transcription import transcribe_audio


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-dlp-subs",
        description="Download online video audio and generate an SRT subtitle file with Groq.",
    )
    parser.add_argument("url", help="Video URL supported by yt-dlp.")
    parser.add_argument(
        "--groq-api-key",
        default=os.environ.get("GROQ_API_KEY"),
        help="Groq API key. Defaults to GROQ_API_KEY.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path for the generated .srt file. Defaults to the video title.",
    )
    parser.add_argument(
        "--model",
        default="whisper-large-v3-turbo",
        help="Groq transcription model. Common values: whisper-large-v3-turbo, whisper-large-v3.",
    )
    parser.add_argument(
        "--language",
        help="Optional ISO-639-1 source language hint, for example en.",
    )
    parser.add_argument(
        "--prompt",
        help="Optional transcription prompt with context, spelling, or names.",
    )
    parser.add_argument(
        "--audio-format",
        default="mp3",
        choices=["mp3", "m4a", "wav", "flac", "opus"],
        help="Audio format produced by yt-dlp/ffmpeg before transcription.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Copy the extracted audio next to the subtitle file.",
    )
    parser.add_argument(
        "--keep-video",
        action="store_true",
        help="Keep the downloaded video file next to the subtitle file.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce yt-dlp output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.groq_api_key:
        parser.error("missing --groq-api-key or GROQ_API_KEY")

    try:
        with download_audio(
            args.url,
            audio_format=args.audio_format,
            quiet=args.quiet,
            keep_video=args.keep_video,
        ) as downloaded:
            output_path = _resolve_output_path(args.output, downloaded.title)
            _status(f"Transcribing audio with {args.model}...", quiet=args.quiet)
            segments = transcribe_audio(
                downloaded.audio_path,
                api_key=args.groq_api_key,
                model=args.model,
                language=args.language,
                prompt=args.prompt,
            )

            if not segments:
                raise RuntimeError("Groq returned no transcription text")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(to_srt(segments), encoding="utf-8")

            if args.keep_audio:
                audio_copy = output_path.with_suffix(downloaded.audio_path.suffix)
                audio_copy.write_bytes(downloaded.audio_path.read_bytes())
                _status(f"Saved audio: {audio_copy}", quiet=args.quiet)

            if args.keep_video and downloaded.video_path is not None:
                video_copy = output_path.with_suffix(downloaded.video_path.suffix)
                video_copy.write_bytes(downloaded.video_path.read_bytes())
                _status(f"Saved video: {video_copy}", quiet=args.quiet)

            print(f"Saved subtitles: {output_path}")
            return 0
    except (DownloadFailure, GroqError, RuntimeError, OSError) as exc:
        print(f"yt-dlp-subs: error: {exc}", file=sys.stderr)
        return 1


def _resolve_output_path(output: Path | None, title: str) -> Path:
    if output is not None:
        return output.with_suffix(".srt") if output.suffix == "" else output
    return Path(f"{output_stem_from_title(title)}.srt")


def _status(message: str, *, quiet: bool) -> None:
    if not quiet:
        print(message, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
