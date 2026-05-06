# yt-dlp-subs

Command line subtitle generation for online videos. It uses `yt-dlp` to extract audio and Groq's Whisper transcription endpoint to produce an `.srt` subtitle file.

## Install

```bash
pyenv local 3.11.11
pyenv exec python3.11 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

You also need `ffmpeg` available on your `PATH`, because `yt-dlp` uses it to extract audio.

## Usage

```bash
yt-dlp-subs "https://www.youtube.com/watch?v=d0b6ECKU_Os" --groq-api-key="$GROQ_API_KEY"
```

You can also set the API key once:

```bash
export GROQ_API_KEY="gsk_..."
yt-dlp-subs "https://www.youtube.com/watch?v=d0b6ECKU_Os"
```

Useful options:

```bash
yt-dlp-subs URL \
  --output subtitles.srt \
  --model whisper-large-v3 \
  --language en \
  --prompt "Technical talk with Python package names" \
  --keep-audio
```

The default model is `whisper-large-v3-turbo`. Use `whisper-large-v3` when accuracy is more important than speed.
