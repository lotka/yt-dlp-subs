from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Iterable


@dataclass(frozen=True)
class SubtitleSegment:
    start: float
    end: float
    text: str


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0

    milliseconds_total = round(seconds * 1000)
    milliseconds = milliseconds_total % 1000
    seconds_total = milliseconds_total // 1000
    secs = seconds_total % 60
    minutes_total = seconds_total // 60
    mins = minutes_total % 60
    hours = minutes_total // 60
    return f"{hours:02}:{mins:02}:{secs:02},{milliseconds:03}"


def to_srt(segments: Iterable[SubtitleSegment]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        text = _clean_text(segment.text)
        if not text:
            continue

        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}",
                    text,
                ]
            )
        )

    return "\n\n".join(blocks) + ("\n" if blocks else "")


def _clean_text(text: str) -> str:
    return escape(" ".join(text.split()), quote=False)

