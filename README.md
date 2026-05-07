# yt-dlp-subs

Command line subtitle generation for online videos. It uses `yt-dlp` to extract audio and Groq's Whisper transcription endpoint to produce an `.srt` subtitle file.

## Install

TODO

## Usage

```bash
yt-dlp-subs "https://www.youtube.com/watch?v=d0b6ECKU_Os" --groq-api-key="$GROQ_API_KEY"
```

You can also set the API key once via an environment variable:

```bash
export GROQ_API_KEY="gsk_..."
yt-dlp-subs "https://www.youtube.com/watch?v=d0b6ECKU_Os"
```

Or save it permanently to a local config file so you never need to pass it again:

```bash
mkdir -p ~/.config/yt-dlp-subs
echo "GROQ_API_KEY=gsk_..." > ~/.config/yt-dlp-subs/config
```

The key is resolved in this order: `--groq-api-key` flag → `GROQ_API_KEY` env var → config file.

Check the installed version:

```bash
yt-dlp-subs --version
```

Useful options:

```bash
yt-dlp-subs URL \
  --output subtitles.srt \
  --model whisper-large-v3 \
  --language en \
  --prompt "Technical talk with Python package names" \
  --temperature 0.2 \
  --keep-audio \
  --keep-video
```

The default model is `whisper-large-v3-turbo`. Use `whisper-large-v3` when accuracy is more important than speed. The default temperature is `0.0` (fully deterministic); increase it slightly (e.g. `0.2`) if the transcription feels too repetitive.
