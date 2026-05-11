import subprocess
from pathlib import Path
from types import SimpleNamespace

from yt_dlp_subs.srt import SubtitleSegment
from yt_dlp_subs.transcription import (
    prepare_audio_for_groq,
    segments_from_response,
    transcribe_audio,
)


FFMPEG_QUIET_FLAGS = ["-nostdin", "-hide_banner", "-nostats", "-loglevel", "error"]


def test_prepare_audio_for_groq_downsamples_to_mono_mp3(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.wav"
    output = tmp_path / "groq.mp3"
    source.write_bytes(b"audio")
    commands = []

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))
        output.write_bytes(b"prepared")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("yt_dlp_subs.transcription.subprocess.run", fake_run)

    prepare_audio_for_groq(source, output)

    assert output.read_bytes() == b"prepared"
    command, kwargs = commands[0]
    assert command == [
        "ffmpeg",
        "-y",
        *FFMPEG_QUIET_FLAGS,
        "-i",
        str(source),
        "-vn",
        "-map",
        "0:a:0",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "48k",
        str(output),
    ]
    assert kwargs == {"check": True, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}


def test_transcribe_audio_uploads_prepared_audio_when_under_limit(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"audio")
    uploads = []

    class FakeTranscriptions:
        def create(self, **kwargs):
            uploads.append(kwargs)
            return {"segments": [{"start": 0, "end": 1.5, "text": "hello"}]}

    class FakeAudio:
        transcriptions = FakeTranscriptions()

    class FakeGroq:
        audio = FakeAudio()

        def __init__(self, api_key):
            assert api_key == "gsk_test"

    def fake_run(command, **kwargs):
        Path(command[-1]).write_bytes(b"prepared")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("yt_dlp_subs.transcription.Groq", FakeGroq)
    monkeypatch.setattr("yt_dlp_subs.transcription.subprocess.run", fake_run)

    assert transcribe_audio(source, api_key="gsk_test") == [SubtitleSegment(0.0, 1.5, "hello")]
    assert uploads[0]["file"] == ("audio.mp3", b"prepared")
    assert uploads[0]["model"] == "whisper-large-v3-turbo"
    assert uploads[0]["response_format"] == "verbose_json"
    assert uploads[0]["timestamp_granularities"] == ["segment"]


def test_transcribe_audio_chunks_prepared_audio_over_limit(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"audio")
    uploads = []
    commands = []

    class FakeTranscriptions:
        def create(self, **kwargs):
            uploads.append(kwargs)
            index = len(uploads)
            start = 1 if index == 1 else 6
            return {"segments": [{"start": start, "end": start + 1, "text": f"chunk {index}"}]}

    class FakeAudio:
        transcriptions = FakeTranscriptions()

    class FakeGroq:
        audio = FakeAudio()

        def __init__(self, api_key):
            assert api_key == "gsk_test"

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[0] == "ffprobe":
            return subprocess.CompletedProcess(command, 0, stdout=b"1201.0")
        output = Path(command[-1])
        if output.name == "audio.mp3":
            output.write_bytes(b"larger than test limit")
        else:
            output.write_bytes(b"ok")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("yt_dlp_subs.transcription.MAX_DIRECT_UPLOAD_BYTES", 5)
    monkeypatch.setattr("yt_dlp_subs.transcription.Groq", FakeGroq)
    monkeypatch.setattr("yt_dlp_subs.transcription.subprocess.run", fake_run)

    assert transcribe_audio(source, api_key="gsk_test") == [
        SubtitleSegment(1.0, 2.0, "chunk 1"),
        SubtitleSegment(606.0, 607.0, "chunk 2"),
        SubtitleSegment(1206.0, 1207.0, "chunk 3"),
    ]
    assert [upload["file"][0] for upload in uploads] == [
        "chunk-0000.mp3",
        "chunk-0001.mp3",
        "chunk-0002.mp3",
    ]
    chunk_starts = [command[command.index("-ss") + 1] for command in commands if "-ss" in command]
    assert chunk_starts == ["0.000", "600.000", "1200.000"]


def test_segments_from_dict_response() -> None:
    response = {
        "segments": [
            {"start": 0, "end": 2.4, "text": "First"},
            {"start": 2.4, "end": 3, "text": "   "},
        ]
    }

    assert segments_from_response(response) == [SubtitleSegment(0.0, 2.4, "First")]


def test_segments_from_object_response_falls_back_to_text() -> None:
    response = SimpleNamespace(text="Only text")

    assert segments_from_response(response) == [SubtitleSegment(0.0, 1.0, "Only text")]
