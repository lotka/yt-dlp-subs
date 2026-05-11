from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from urllib.parse import unquote, urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, sanitize_filename


class DownloadFailure(RuntimeError):
    pass


class DownloadedAudio:
    def __init__(
        self,
        temp_dir: TemporaryDirectory[str],
        audio_path: Path,
        title: str,
        video_path: Path | None = None,
        source_path: Path | None = None,
    ) -> None:
        self._temp_dir = temp_dir
        self.audio_path = audio_path
        self.title = title
        self.video_path = video_path
        self.source_path = source_path

    def cleanup(self) -> None:
        self._temp_dir.cleanup()

    def __enter__(self) -> "DownloadedAudio":
        return self

    def __exit__(self, *_: object) -> None:
        self.cleanup()


def download_audio(
    source: str,
    *,
    audio_format: str = "mp3",
    quiet: bool = False,
    keep_video: bool = False,
    video_format: str | None = None,
) -> DownloadedAudio:
    local_path = _local_path_from_source(source)
    if local_path is not None:
        return _extract_local_audio(
            local_path,
            audio_format=audio_format,
            quiet=quiet,
            keep_video=keep_video,
            video_format=video_format,
        )
    return _download_audio_from_url(
        source,
        audio_format=audio_format,
        quiet=quiet,
        keep_video=keep_video,
        video_format=video_format,
    )


def _download_audio_from_url(
    url: str,
    *,
    audio_format: str,
    quiet: bool,
    keep_video: bool,
    video_format: str | None = None,
) -> DownloadedAudio:
    if keep_video:
        return _download_video_from_url(
            url,
            audio_format=audio_format,
            quiet=quiet,
            video_format=video_format,
        )

    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-")
    temp_path = Path(temp_dir.name)
    outtmpl = str(temp_path / "audio.%(ext)s")

    options = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": quiet,
        "no_warnings": True,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
            }
        ],
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as exc:
        temp_dir.cleanup()
        raise DownloadFailure(str(exc)) from exc

    title = _title_from_info(info)
    audio_path = _find_audio_file(temp_path, audio_format)
    if audio_path is None:
        temp_dir.cleanup()
        raise DownloadFailure("yt-dlp completed but no audio file was produced")

    return DownloadedAudio(temp_dir, audio_path, title)


def _download_video_from_url(
    url: str,
    *,
    audio_format: str,
    quiet: bool,
    video_format: str | None = None,
) -> DownloadedAudio:
    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-")
    temp_path = Path(temp_dir.name)

    options = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": str(temp_path / "video.%(ext)s"),
        "quiet": quiet,
        "no_warnings": True,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as exc:
        temp_dir.cleanup()
        raise DownloadFailure(str(exc)) from exc

    title = _title_from_info(info)
    video_path = _find_downloaded_video_file(temp_path)
    if video_path is None:
        temp_dir.cleanup()
        raise DownloadFailure("yt-dlp completed but no video file was produced")

    audio_path = temp_path / f"audio.{audio_format}"
    try:
        _extract_audio_to_path(video_path, audio_path, quiet=quiet)
        if video_format and video_path.suffix.lower().lstrip(".") != video_format:
            video_path = _convert_video(video_path, video_format, quiet=quiet)
    except DownloadFailure:
        temp_dir.cleanup()
        raise

    return DownloadedAudio(temp_dir, audio_path, title, video_path=video_path)


_ALLOWED_EXTENSIONS = {
    "aac", "aiff", "alac", "flac", "m4a", "mp3", "ogg", "opus", "wav", "wma",
    "avi", "flv", "m4v", "mkv", "mov", "mp4", "mpg", "mpeg", "ogv", "ts", "webm", "wmv",
}


def _extract_local_audio(
    path: Path,
    *,
    audio_format: str,
    quiet: bool,
    keep_video: bool,
    video_format: str | None = None,
) -> DownloadedAudio:
    if path.suffix.lower().lstrip(".") not in _ALLOWED_EXTENSIONS:
        raise DownloadFailure(
            f"{path.name} is not a supported video or audio file. "
            f"Supported formats: {', '.join(sorted(_ALLOWED_EXTENSIONS))}."
        )

    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-")
    temp_path = Path(temp_dir.name)
    audio_path = temp_path / f"audio.{audio_format}"
    try:
        _extract_audio_to_path(path, audio_path, quiet=quiet)
    except DownloadFailure:
        temp_dir.cleanup()
        raise

    video_path = None
    if keep_video and not _looks_like_audio_file(path):
        video_path = temp_path / path.name
        shutil.copy2(path, video_path)
        if video_format and video_path.suffix.lower().lstrip(".") != video_format:
            try:
                video_path = _convert_video(video_path, video_format, quiet=quiet)
            except DownloadFailure:
                temp_dir.cleanup()
                raise

    return DownloadedAudio(
        temp_dir,
        audio_path,
        path.stem,
        video_path=video_path,
        source_path=path,
    )


def _convert_video(source_path: Path, target_format: str, *, quiet: bool) -> Path:
    output_path = source_path.with_suffix(f".{target_format}")
    command = ["ffmpeg", "-y", "-i", str(source_path)]
    if target_format == "mp4":
        command += ["-c:v", "libx264", "-c:a", "aac"]
    command.append(str(output_path))
    if quiet:
        command[1:1] = ["-nostats", "-loglevel", "error"]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise DownloadFailure("ffmpeg was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        raise DownloadFailure(f"ffmpeg could not convert video to {target_format}: {detail}") from exc
    return output_path


def _extract_audio_to_path(source_path: Path, audio_path: Path, *, quiet: bool) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-nostdin",
        "-hide_banner",
        "-nostats",
        "-loglevel",
        "error",
        "-i",
        str(source_path),
        "-vn",
        str(audio_path),
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise DownloadFailure("ffmpeg was not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        message = f"ffmpeg could not extract audio from {source_path}"
        if detail:
            message = f"{message}: {detail}"
        raise DownloadFailure(message) from exc

    if not audio_path.exists():
        raise DownloadFailure("ffmpeg completed but no audio file was produced")


def output_stem_from_title(title: str) -> str:
    return sanitize_filename(title, restricted=True) or "subtitles"


def _find_audio_file(directory: Path, audio_format: str) -> Path | None:
    expected = directory / f"audio.{audio_format}"
    if expected.exists():
        return expected

    candidates = [path for path in _files(directory) if path.suffix and not path.name.endswith(".part")]
    if len(candidates) == 1:
        return candidates[0]
    return next((path for path in candidates if path.suffix.lstrip(".") == audio_format), None)


def _find_downloaded_video_file(directory: Path) -> Path | None:
    candidates = [
        path
        for path in _files(directory)
        if path.suffix and not path.name.endswith(".part")
    ]
    if len(candidates) == 1:
        return candidates[0]

    exact_stem = [path for path in candidates if path.stem == "video"]
    if len(exact_stem) == 1:
        return exact_stem[0]

    video_candidates = [path for path in candidates if not _looks_like_audio_file(path)]
    if len(video_candidates) == 1:
        return video_candidates[0]
    if video_candidates:
        return max(video_candidates, key=lambda path: path.stat().st_size)
    return None


def _files(directory: Path) -> Iterator[Path]:
    for path in directory.iterdir():
        if path.is_file():
            yield path


def _local_path_from_source(source: str) -> Path | None:
    parsed = urlparse(source)
    if parsed.scheme == "file":
        path = Path(unquote(parsed.path)).expanduser()
    else:
        path = Path(source).expanduser()

    try:
        if path.is_file():
            return path
    except OSError:
        return None
    return None


def _looks_like_audio_file(path: Path) -> bool:
    return path.suffix.lower().lstrip(".") in {
        "aac",
        "aiff",
        "alac",
        "flac",
        "m4a",
        "mp3",
        "ogg",
        "opus",
        "wav",
        "wma",
    }


def _title_from_info(info: object) -> str:
    if isinstance(info, dict):
        title = info.get("title")
        if isinstance(title, str) and title.strip():
            return title
        webpage_url = info.get("webpage_url")
        if isinstance(webpage_url, str) and webpage_url.strip():
            return webpage_url
    return "subtitles"
