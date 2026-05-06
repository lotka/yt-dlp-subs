# CLAUDE.md — yt-dlp-subs

## Project Purpose

CLI tool that generates `.srt` subtitle files for any online video. It extracts audio via `yt-dlp` (supports YouTube, Vimeo, etc.) and transcribes it using [Groq's Whisper API](https://console.groq.com).

## Architecture

Clean four-stage pipeline, one module per concern:

```
User Input (CLI)
    ↓
cli.py          — parse args, orchestrate, save output
    ↓
downloader.py   — extract audio via yt-dlp + FFmpeg (temp dir)
    ↓
transcription.py— send audio to Groq Whisper, parse segments
    ↓
srt.py          — format SubtitleSegments → valid .srt string
    ↓
Output: <title>.srt (+ optional audio/video files)
```

## File Structure

```
src/yt_dlp_subs/
├── __init__.py        version = "0.1.0"
├── cli.py             entry point (build_parser, main, _resolve_output_path)
├── downloader.py      DownloadedAudio context manager, download_audio()
├── transcription.py   transcribe_audio(), segments_from_response()
└── srt.py             SubtitleSegment dataclass, to_srt(), format_timestamp()
tests/
├── test_cli.py
├── test_srt.py
└── test_transcription.py
```

## Key Types

- `SubtitleSegment` (frozen dataclass in `srt.py`): `start: float`, `end: float`, `text: str`
- `DownloadedAudio` (context manager in `downloader.py`): holds `audio_path`, `title`, `video_path`; calls `cleanup()` on exit
- `DownloadFailure` — custom exception raised by `download_audio()`

## Dependencies

| Package | Version | Role |
|---------|---------|------|
| `groq` | >=0.9.0 | Groq API client (Whisper endpoint) |
| `yt-dlp` | >=2024.8.6 | Audio/video extraction |
| `pytest` | >=8.0 (dev) | Test runner |
| `hatchling` | (build) | Build backend |

**System requirement**: `ffmpeg` must be on `PATH` — yt-dlp calls it to extract/convert audio.

## How to Run Locally

### 1. Install system dependencies (macOS)

If you don't have Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Install pyenv and ffmpeg:

```bash
brew install pyenv ffmpeg
```

Add pyenv to your shell (create `~/.zshrc` if it doesn't exist):

```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc
```

### 2. Install Python and set up the project

```bash
pyenv install 3.11.11
pyenv local 3.11.11
pyenv exec python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Get a Groq API key

Sign up for free at https://console.groq.com and copy your key.

```bash
export GROQ_API_KEY="gsk_..."
```

### 4. Run

```bash
yt-dlp-subs "https://www.youtube.com/watch?v=d0b6ECKU_Os"
```

> Run `source .venv/bin/activate` every time you open a new terminal in this project.

**Run tests:**

```bash
pytest tests/
```

## CLI Reference

```
yt-dlp-subs URL [options]

Required:
  url                   Any URL supported by yt-dlp

Auth:
  --groq-api-key KEY    Groq API key (or set GROQ_API_KEY env var)

Output:
  -o, --output PATH     Output .srt path (default: <video_title>.srt)
  --keep-audio          Copy extracted audio alongside the .srt file
  --keep-video          Keep downloaded video alongside the .srt file

Transcription:
  --model MODEL         Groq Whisper model (default: whisper-large-v3-turbo)
                        Use whisper-large-v3 for higher accuracy
  --language LANG       ISO-639-1 language hint (e.g. "en", "fr")
  --prompt TEXT         Context hint to improve transcription (e.g. proper nouns)
  --audio-format FMT    mp3 (default), m4a, wav, flac, opus

Misc:
  --quiet               Suppress yt-dlp progress output
```

## External Services

- **Groq Whisper API** — `client.audio.transcriptions.create()`, response format `verbose_json`, timestamp granularity `segment`, temperature `0.0`.

## Design Notes

- Temporary files live in a `yt-dlp-subs-*` prefix temp dir and are cleaned up by `DownloadedAudio.cleanup()` even on error.
- `segments_from_response()` handles both structured segment objects and plain-text fallback from the API.
- `_clean_text()` normalises whitespace and escapes HTML entities (`<`, `>`, `&`) before writing SRT.
- `output_stem_from_title()` sanitises the video title into a valid filename (strips forbidden chars, trims length).
