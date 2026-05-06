from yt_dlp_subs.srt import SubtitleSegment, format_timestamp, to_srt


def test_format_timestamp_rounds_to_milliseconds() -> None:
    assert format_timestamp(3723.4567) == "01:02:03,457"


def test_to_srt_writes_numbered_blocks_and_escapes_text() -> None:
    srt = to_srt(
        [
            SubtitleSegment(start=0, end=1.25, text=" Hello   world "),
            SubtitleSegment(start=1.25, end=2.5, text="A < B"),
        ]
    )

    assert srt == (
        "1\n"
        "00:00:00,000 --> 00:00:01,250\n"
        "Hello world\n"
        "\n"
        "2\n"
        "00:00:01,250 --> 00:00:02,500\n"
        "A &lt; B\n"
    )

