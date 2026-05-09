import subprocess
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from yt_dlp_subs.cli import build_parser, main, _resolve_output_path, _same_path
from yt_dlp_subs.downloader import DownloadedAudio
from yt_dlp_subs.srt import SubtitleSegment


@pytest.fixture
def parse():
    def _parse(*extra):
        return build_parser().parse_args(["https://example.com/video", *extra])
    return _parse


def test_defaults(parse):
    args = parse()
    assert args.source == "https://example.com/video"
    assert args.model == "whisper-large-v3-turbo"
    assert args.audio_format == "mp3"
    assert args.temperature == 0.0
    assert args.language is None
    assert args.prompt is None
    assert args.output is None
    assert args.keep_audio is False
    assert args.keep_video is True
    assert args.quiet is False
    assert args.open is False


def test_keep_audio(parse):
    assert parse("--keep-audio").keep_audio is True


def test_keep_video(parse):
    assert parse("--keep-video").keep_video is True


def test_no_keep_video(parse):
    assert parse("--no-keep-video").keep_video is False


def test_open_flag(parse):
    assert parse("--open").open is True


def test_quiet(parse):
    assert parse("--quiet").quiet is True


def test_model(parse):
    assert parse("--model", "whisper-large-v3").model == "whisper-large-v3"


def test_language(parse):
    assert parse("--language", "fr").language == "fr"


def test_prompt(parse):
    assert parse("--prompt", "Python talk").prompt == "Python talk"


def test_temperature(parse):
    assert parse("--temperature", "0.2").temperature == pytest.approx(0.2)


def test_audio_format(parse):
    assert parse("--audio-format", "wav").audio_format == "wav"


def test_output(parse):
    assert parse("--output", "out.srt").output == Path("out.srt")


def test_resolve_output_path_uses_title_when_no_output():
    assert _resolve_output_path(None, "My Video") == Path("My_Video.srt")


def test_resolve_output_path_uses_explicit_output():
    assert _resolve_output_path(Path("custom.srt"), "ignored") == Path("custom.srt")


def test_resolve_output_path_appends_srt_extension():
    assert _resolve_output_path(Path("custom"), "ignored") == Path("custom.srt")


def test_same_path_matches_equivalent_paths(tmp_path):
    path = tmp_path / "sample.mkv"
    path.write_bytes(b"video")

    assert _same_path(path, tmp_path / "." / "sample.mkv") is True


def test_same_path_handles_missing_right_path(tmp_path):
    assert _same_path(tmp_path / "sample.mkv", None) is False


def test_main_embeds_subtitles_when_default_output_matches_source(tmp_path, monkeypatch):
    source = tmp_path / "sample.mkv"
    source.write_bytes(b"original video")
    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-test-")
    temp_path = Path(temp_dir.name)
    audio_path = temp_path / "audio.mp3"
    video_path = temp_path / "sample.mkv"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"temporary video copy")

    def fake_download_audio(source_arg, **kwargs):
        assert source_arg == str(source)
        assert kwargs["keep_video"] is True
        return DownloadedAudio(
            temp_dir,
            audio_path,
            "sample",
            video_path=video_path,
            source_path=source,
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("yt_dlp_subs.cli.download_audio", fake_download_audio)
    monkeypatch.setattr(
        "yt_dlp_subs.cli.transcribe_audio",
        lambda *args, **kwargs: [SubtitleSegment(0, 1, "hello")],
    )
    monkeypatch.setattr("yt_dlp_subs.cli.subprocess.run", _fake_embed_subtitles_run(b"embedded video"))

    assert main([str(source), "--groq-api-key", "gsk_test", "--quiet"]) == 0
    assert source.read_bytes() == b"embedded video"
    assert (tmp_path / "sample.srt").exists()


def test_main_embeds_subtitles_when_output_does_not_match_source(tmp_path, monkeypatch):
    source = tmp_path / "sample.mkv"
    output = tmp_path / "transcript.srt"
    source.write_bytes(b"original video")
    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-test-")
    temp_path = Path(temp_dir.name)
    audio_path = temp_path / "audio.mp3"
    video_path = temp_path / "sample.mkv"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"temporary video copy")

    def fake_download_audio(source_arg, **kwargs):
        assert source_arg == str(source)
        assert kwargs["keep_video"] is True
        return DownloadedAudio(
            temp_dir,
            audio_path,
            "sample",
            video_path=video_path,
            source_path=source,
        )

    monkeypatch.setattr("yt_dlp_subs.cli.download_audio", fake_download_audio)
    monkeypatch.setattr(
        "yt_dlp_subs.cli.transcribe_audio",
        lambda *args, **kwargs: [SubtitleSegment(0, 1, "hello")],
    )
    monkeypatch.setattr("yt_dlp_subs.cli.subprocess.run", _fake_embed_subtitles_run(b"embedded video"))

    assert main([str(source), "--keep-video", "--output", str(output), "--groq-api-key", "gsk_test", "--quiet"]) == 0
    assert source.read_bytes() == b"original video"
    assert (tmp_path / "transcript.mkv").read_bytes() == b"embedded video"


def test_main_embeds_mp4_subtitles_as_mov_text(tmp_path, monkeypatch):
    source = tmp_path / "sample.mp4"
    output = tmp_path / "transcript.srt"
    source.write_bytes(b"original video")
    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-test-")
    temp_path = Path(temp_dir.name)
    audio_path = temp_path / "audio.mp3"
    video_path = temp_path / "sample.mp4"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"temporary video copy")
    commands = []

    def fake_download_audio(source_arg, **kwargs):
        return DownloadedAudio(
            temp_dir,
            audio_path,
            "sample",
            video_path=video_path,
            source_path=source,
        )

    monkeypatch.setattr("yt_dlp_subs.cli.download_audio", fake_download_audio)
    monkeypatch.setattr(
        "yt_dlp_subs.cli.transcribe_audio",
        lambda *args, **kwargs: [SubtitleSegment(0, 1, "hello")],
    )
    monkeypatch.setattr("yt_dlp_subs.cli.subprocess.run", _fake_embed_subtitles_run(b"embedded video", commands))

    assert main([str(source), "--keep-video", "--output", str(output), "--groq-api-key", "gsk_test", "--quiet"]) == 0
    assert (tmp_path / "transcript.mp4").read_bytes() == b"embedded video"
    assert commands[0][commands[0].index("-c:s") + 1] == "mov_text"


def test_main_with_all_options(tmp_path, monkeypatch):
    source = tmp_path / "sample.mkv"
    source.write_bytes(b"original video")
    output = tmp_path / "subtitles.srt"
    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-test-")
    temp_path = Path(temp_dir.name)
    audio_path = temp_path / "audio.wav"
    video_path = temp_path / "sample.mkv"
    audio_path.write_bytes(b"audio")
    video_path.write_bytes(b"video copy")

    download_kwargs = {}
    transcribe_kwargs = {}
    open_calls = []

    def fake_download_audio(source_arg, **kwargs):
        download_kwargs.update(kwargs)
        return DownloadedAudio(temp_dir, audio_path, "sample", video_path=video_path, source_path=source)

    def fake_transcribe_audio(audio_path, **kwargs):
        transcribe_kwargs.update(kwargs)
        return [SubtitleSegment(0, 1, "hello")]

    monkeypatch.setattr("yt_dlp_subs.cli.download_audio", fake_download_audio)
    monkeypatch.setattr("yt_dlp_subs.cli.transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr("yt_dlp_subs.cli._open_in_explorer", lambda path: open_calls.append(path))
    monkeypatch.setattr("yt_dlp_subs.cli.subprocess.run", _fake_embed_subtitles_run(b"embedded video"))

    result = main([
        str(source),
        "--groq-api-key", "gsk_test",
        "--output", str(output),
        "--model", "whisper-large-v3",
        "--language", "en",
        "--prompt", "Me at the zoo",
        "--temperature", "0.2",
        "--audio-format", "wav",
        "--keep-audio",
        "--keep-video",
        "--open",
        "--quiet",
    ])

    assert result == 0
    assert download_kwargs["audio_format"] == "wav"
    assert download_kwargs["keep_video"] is True
    assert transcribe_kwargs["model"] == "whisper-large-v3"
    assert transcribe_kwargs["language"] == "en"
    assert transcribe_kwargs["prompt"] == "Me at the zoo"
    assert transcribe_kwargs["temperature"] == pytest.approx(0.2)
    assert output.exists()
    assert (tmp_path / "subtitles.wav").exists()
    assert (tmp_path / "subtitles.mkv").read_bytes() == b"embedded video"
    assert len(open_calls) == 1


def test_main_passes_no_keep_video_to_downloader(tmp_path, monkeypatch):
    source = tmp_path / "sample.mkv"
    source.write_bytes(b"original video")
    temp_dir = TemporaryDirectory(prefix="yt-dlp-subs-test-")
    temp_path = Path(temp_dir.name)
    audio_path = temp_path / "audio.mp3"
    audio_path.write_bytes(b"audio")

    def fake_download_audio(source_arg, **kwargs):
        assert source_arg == str(source)
        assert kwargs["keep_video"] is False
        return DownloadedAudio(temp_dir, audio_path, "sample", source_path=source)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("yt_dlp_subs.cli.download_audio", fake_download_audio)
    monkeypatch.setattr(
        "yt_dlp_subs.cli.transcribe_audio",
        lambda *args, **kwargs: [SubtitleSegment(0, 1, "hello")],
    )

    assert main([str(source), "--no-keep-video", "--groq-api-key", "gsk_test", "--quiet"]) == 0
    assert source.read_bytes() == b"original video"
    assert (tmp_path / "sample.srt").exists()


def _fake_embed_subtitles_run(video_bytes, commands=None):
    def fake_run(command, **kwargs):
        if commands is not None:
            commands.append(command)
        Path(command[-1]).write_bytes(video_bytes)
        return subprocess.CompletedProcess(command, 0)

    return fake_run
