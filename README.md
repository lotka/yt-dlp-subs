# yt-dlp-subs

Command line subtitle generation for online videos. It uses `yt-dlp` to extract audio and Groq's Whisper transcription endpoint to produce an `.srt` subtitle file.

## Install

Requires Python 3.10 or newer and `ffmpeg` on your `PATH`. `yt-dlp` uses
`ffmpeg` to extract audio before the file is sent to Groq for transcription.

On macOS:

```bash
brew install ffmpeg
```

On Linux:

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

On Windows, install `ffmpeg` with one of these package managers, then open a
new PowerShell window:

```powershell
# winget
winget install Gyan.FFmpeg

# Chocolatey
choco install ffmpeg

# Scoop
scoop install ffmpeg
```

Install the CLI from this checkout.

On macOS/Linux:

```bash
bash install.sh
```

On Windows (PowerShell):

```powershell
.\install.ps1
```

If the `yt-dlp-subs` command is not found after install, open a new terminal.

For local development, install it in editable mode with the test dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

On Windows:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

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
