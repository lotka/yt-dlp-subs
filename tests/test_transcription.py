from types import SimpleNamespace

from yt_dlp_subs.srt import SubtitleSegment
from yt_dlp_subs.transcription import segments_from_response


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

