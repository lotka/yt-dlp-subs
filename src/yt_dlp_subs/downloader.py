from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator

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
    ) -> None:
        self._temp_dir = temp_dir
        self.audio_path = audio_path
        self.title = title
        self.video_path = video_path

    def cleanup(self) -> None:
        self._temp_dir.cleanup()

    def __enter__(self) -> "DownloadedAudio":
        return self

    def __exit__(self, *_: object) -> None:
        self.cleanup()


def download_audio(
    url: str,
    *,
    audio_format: str = "mp3",
    quiet: bool = False,
    keep_video: bool = False,
) -> DownloadedAudio:
    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-")
    temp_path = Path(temp_dir.name)
    outtmpl = str(temp_path / ("video.%(ext)s" if keep_video else "audio.%(ext)s"))

    options = {
        "format": "bestvideo+bestaudio/best" if keep_video else "bestaudio/best",
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

    if keep_video:
        options["keepvideo"] = True

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

    video_path = _find_video_file(temp_path, audio_path) if keep_video else None
    if keep_video and video_path is None:
        temp_dir.cleanup()
        raise DownloadFailure("yt-dlp completed but no video file was produced")

    return DownloadedAudio(temp_dir, audio_path, title, video_path=video_path)


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


def _find_video_file(directory: Path, audio_path: Path) -> Path | None:
    candidates = [
        path
        for path in _files(directory)
        if path != audio_path and not path.name.endswith(".part")
    ]
    if len(candidates) == 1:
        return candidates[0]
    return next((path for path in candidates if path.suffix != audio_path.suffix), None)


def _files(directory: Path) -> Iterator[Path]:
    for path in directory.iterdir():
        if path.is_file():
            yield path


def _title_from_info(info: object) -> str:
    if isinstance(info, dict):
        title = info.get("title")
        if isinstance(title, str) and title.strip():
            return title
        webpage_url = info.get("webpage_url")
        if isinstance(webpage_url, str) and webpage_url.strip():
            return webpage_url
    return "subtitles"

