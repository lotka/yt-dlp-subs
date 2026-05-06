# yt-dlp-subs

Command line subtitle generation for online videos. It uses `yt-dlp` to extract audio and Groq's Whisper transcription endpoint to produce an `.srt` subtitle file.

## Install

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

> You need to run `source .venv/bin/activate` every time you open a new terminal in this project.

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
  --keep-audio \
  --keep-video
```

The default model is `whisper-large-v3-turbo`. Use `whisper-large-v3` when accuracy is more important than speed.
