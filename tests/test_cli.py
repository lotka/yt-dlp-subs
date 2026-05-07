import pytest
from pathlib import Path

from yt_dlp_subs.cli import build_parser, _resolve_output_path


@pytest.fixture
def parse():
    def _parse(*extra):
        return build_parser().parse_args(["https://example.com", *extra])
    return _parse


def test_defaults(parse):
    args = parse()
    assert args.model == "whisper-large-v3-turbo"
    assert args.audio_format == "mp3"
    assert args.temperature == 0.0
    assert args.language is None
    assert args.prompt is None
    assert args.output is None
    assert args.keep_audio is False
    assert args.keep_video is False
    assert args.quiet is False
    assert args.open is False


def test_keep_audio(parse):
    assert parse("--keep-audio").keep_audio is True


def test_keep_video(parse):
    assert parse("--keep-video").keep_video is True


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
