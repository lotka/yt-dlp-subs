from __future__ import annotations

import argparse
import os
import platform
import re
import subprocess
from contextlib import nullcontext
from pathlib import Path

from rich.console import Console
from groq import GroqError

from yt_dlp_subs import __version__
from yt_dlp_subs.downloader import DownloadFailure, download_audio, output_stem_from_title
from yt_dlp_subs.srt import to_srt
from yt_dlp_subs.transcription import transcribe_audio

_console = Console()
_err = Console(stderr=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yt-dlp-subs",
        description="Download online video audio and generate an SRT subtitle file with Groq.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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
        help="Suppress all progress output (yt-dlp and tool status messages).",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the output folder in the file explorer after saving.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for transcription (0.0–1.0, default: 0.0).",
    )
    return parser


def _config_path() -> Path:
    return Path.home() / ".config" / "yt-dlp-subs" / "config"


def _read_config_key() -> str | None:
    path = _config_path()
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("GROQ_API_KEY="):
            return line[len("GROQ_API_KEY="):]
    return None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.groq_api_key:
        args.groq_api_key = _read_config_key()

    if not args.groq_api_key:
        parser.error(
            f"missing --groq-api-key or GROQ_API_KEY env var. "
            f"You can also save it to {_config_path()} as GROQ_API_KEY=gsk_..."
        )

    try:
        _status(f"Model: {args.model}", quiet=args.quiet)
        if args.language:
            _status(f"Language: {args.language}", quiet=args.quiet)
        if args.prompt:
            _status(f"Prompt: {args.prompt}", quiet=args.quiet)
        if args.temperature != 0.0:
            _status(f"Temperature: {args.temperature}", quiet=args.quiet)
        if args.audio_format != "mp3":
            _status(f"Audio format: {args.audio_format}", quiet=args.quiet)
        if args.keep_audio:
            _status("Keeping audio file", quiet=args.quiet)
        if args.keep_video:
            _status("Keeping video file", quiet=args.quiet)
        _status(f"Downloading audio from {args.url}...", quiet=args.quiet)
        with download_audio(
            args.url,
            audio_format=args.audio_format,
            quiet=args.quiet,
            keep_video=args.keep_video,
        ) as downloaded:
            output_path = _resolve_output_path(args.output, downloaded.title)

            spinner = (
                _err.status(f"[cyan]Transcribing audio with {args.model}...[/cyan]")
                if not args.quiet
                else nullcontext()
            )
            with spinner:
                segments = transcribe_audio(
                    downloaded.audio_path,
                    api_key=args.groq_api_key,
                    model=args.model,
                    language=args.language,
                    prompt=args.prompt,
                    temperature=args.temperature,
                )

            if not segments:
                raise RuntimeError("Groq returned no transcription text")

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(to_srt(segments), encoding="utf-8")

            if args.keep_audio:
                audio_copy = output_path.with_suffix(downloaded.audio_path.suffix)
                audio_copy.write_bytes(downloaded.audio_path.read_bytes())
                _status(f"Saved audio: {audio_copy}", quiet=args.quiet)

            if args.keep_video:
                if downloaded.video_path is not None:
                    video_copy = output_path.with_suffix(downloaded.video_path.suffix)
                    video_copy.write_bytes(downloaded.video_path.read_bytes())
                    _status(f"Saved video: {video_copy}", quiet=args.quiet)
                else:
                    _err.print("[yellow]warning:[/yellow] --keep-video was set but no video file was found.")

            _console.print(f"[green]✓[/green] Saved subtitles: {output_path}")

            if args.open:
                _status("Opening in explorer...", quiet=args.quiet)
                _open_in_explorer(output_path.parent)

            return 0
    except (DownloadFailure, GroqError, RuntimeError, OSError) as exc:
        _err.print(f"[red]✗ error:[/red] {_strip_ansi(str(exc))}")
        return 1


def _resolve_output_path(output: Path | None, title: str) -> Path:
    if output is not None:
        return output.with_suffix(".srt") if output.suffix == "" else output
    return Path(f"{output_stem_from_title(title)}.srt")


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _open_in_explorer(path: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", path])
    elif system == "Windows":
        os.startfile(path)
    elif system == "Linux":
        subprocess.run(["xdg-open", path])


def _status(message: str, *, quiet: bool) -> None:
    if not quiet:
        _err.print(f"[cyan]{message}[/cyan]")


if __name__ == "__main__":
    raise SystemExit(main())
