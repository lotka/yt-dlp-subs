import subprocess
from pathlib import Path

import pytest

from yt_dlp_subs.downloader import DownloadFailure, download_audio


FFMPEG_QUIET_FLAGS = ["-nostdin", "-hide_banner", "-nostats", "-loglevel", "error"]


def test_download_audio_keep_video_preserves_merged_url_video(monkeypatch):
    ydl_options = []

    class FakeYoutubeDL:
        def __init__(self, options):
            self.options = options
            ydl_options.append(options)

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def extract_info(self, url, download):
            assert url == "https://example.com/watch"
            assert download is True
            video_path = Path(self.options["outtmpl"].replace("%(ext)s", "mp4"))
            video_path.write_bytes(b"merged video with audio")
            return {"title": "Example Video"}

    def fake_run(command, **kwargs):
        assert Path(command[command.index("-i") + 1]).name == "video.mp4"
        Path(command[-1]).write_bytes(b"audio")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("yt_dlp_subs.downloader.YoutubeDL", FakeYoutubeDL)
    monkeypatch.setattr("yt_dlp_subs.downloader.subprocess.run", fake_run)

    with download_audio("https://example.com/watch", keep_video=True) as downloaded:
        assert downloaded.title == "Example Video"
        assert downloaded.audio_path.name == "audio.mp3"
        assert downloaded.audio_path.read_bytes() == b"audio"
        assert downloaded.video_path is not None
        assert downloaded.video_path.name == "video.mp4"
        assert downloaded.video_path.read_bytes() == b"merged video with audio"

    assert ydl_options[0]["format"] == "bestvideo+bestaudio/best"
    assert "postprocessors" not in ydl_options[0]
    assert "keepvideo" not in ydl_options[0]


def test_download_audio_uses_ffmpeg_for_local_file(tmp_path, monkeypatch):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"video")
    commands = []

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))
        output = Path(command[-1])
        output.write_bytes(b"audio")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("yt_dlp_subs.downloader.subprocess.run", fake_run)

    with download_audio(str(source), audio_format="wav") as downloaded:
        assert downloaded.title == "clip"
        assert downloaded.audio_path.name == "audio.wav"
        assert downloaded.audio_path.read_bytes() == b"audio"
        assert downloaded.video_path is None

    assert commands == [
        (
            ["ffmpeg", "-y", *FFMPEG_QUIET_FLAGS, "-i", str(source), "-vn", commands[0][0][-1]],
            {"check": True, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE},
        )
    ]


def test_download_audio_keeps_local_video_copy(tmp_path, monkeypatch):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"video")

    def fake_run(command, **kwargs):
        Path(command[-1]).write_bytes(b"audio")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("yt_dlp_subs.downloader.subprocess.run", fake_run)

    with download_audio(str(source), keep_video=True) as downloaded:
        assert downloaded.video_path is not None
        assert downloaded.video_path.name == "clip.mp4"
        assert downloaded.video_path.read_bytes() == b"video"
        assert downloaded.video_path == source


def test_download_audio_does_not_treat_local_audio_as_video(tmp_path, monkeypatch):
    source = tmp_path / "voice.mp3"
    source.write_bytes(b"audio source")

    def fake_run(command, **kwargs):
        Path(command[-1]).write_bytes(b"audio")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("yt_dlp_subs.downloader.subprocess.run", fake_run)

    with download_audio(str(source), keep_video=True) as downloaded:
        assert downloaded.video_path is None


def test_download_audio_reports_missing_ffmpeg_for_local_file(tmp_path, monkeypatch):
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"video")

    def fake_run(command, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("yt_dlp_subs.downloader.subprocess.run", fake_run)

    with pytest.raises(DownloadFailure, match="ffmpeg was not found"):
        download_audio(str(source))
