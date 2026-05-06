from yt_dlp_subs.cli import build_parser


def test_build_parser_supports_keep_video() -> None:
    args = build_parser().parse_args(["https://example.com", "--keep-video"])

    assert args.keep_video is True
