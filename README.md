# yt-dlp-subs

Command line subtitle generation for online videos and local media files. It uses `yt-dlp` or `ffmpeg` to extract audio and Groq's Whisper transcription endpoint to produce an `.srt` subtitle file.

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

## Testing

First install the dev dependencies (includes `pytest`):

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

### Unit tests

Run the full test suite (covers CLI flags, SRT formatting, and transcription parsing):

```bash
pytest tests/
```

### End-to-end test

Test with a local video file (all options):

```bash
yt-dlp-subs sample.mkv \
  --groq-api-key "$GROQ_API_KEY" \
  --output subtitles.srt \
  --model whisper-large-v3 \
  --language en \
  --prompt "Me at the zoo" \
  --temperature 0.2 \
  --audio-format mp3 \
  --keep-audio \
  --keep-video \
  --open
```

Test with a YouTube URL (all options):

```bash
yt-dlp-subs "https://www.youtube.com/watch?v=jNQXAC9IVRw" \
  --groq-api-key "$GROQ_API_KEY" \
  --output subtitles.srt \
  --model whisper-large-v3 \
  --language en \
  --prompt "Me at the zoo" \
  --temperature 0.2 \
  --audio-format mp3 \
  --keep-audio \
  --keep-video \
  --open
```

Both should produce a `subtitles.srt` file alongside the audio and a video with the subtitles embedded in the current directory.

You can also run the tool against a local audio or video file:

```bash
yt-dlp-subs ./video.mp4
```

## Contributing

1. Fork the repository and create a branch for your change.
2. Set up the dev environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Make your changes — the project follows a four-stage pipeline: `cli.py` → `downloader.py` → `transcription.py` → `srt.py`.
4. Add or update tests in `tests/` and make sure the full suite passes:
   ```bash
   pytest tests/
   ```
5. Open a pull request with a clear description of what changed and why.

## Usage

```bash
yt-dlp-subs "https://www.youtube.com/watch?v=jNQXAC9IVRw" --groq-api-key="$GROQ_API_KEY"
```

Local audio and video files work the same way:

```bash
yt-dlp-subs ./video.mp4 --groq-api-key="$GROQ_API_KEY"
yt-dlp-subs ./audio.wav --output transcript.srt
```

You can also set the API key once via an environment variable:

```bash
export GROQ_API_KEY="gsk_..."
yt-dlp-subs "https://www.youtube.com/watch?v=jNQXAC9IVRw"
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
yt-dlp-subs SOURCE \
  --output subtitles.srt \
  --model whisper-large-v3 \
  --language en \
  --prompt "Technical talk with Python package names" \
  --temperature 0.2 \
  --keep-audio \
  --no-keep-video \
  --open
```

Pass `--open` to reveal the output folder in Finder (macOS), Explorer (Windows), or the default file manager (Linux) once the subtitle file is saved.

By default, the full downloaded or local video is saved next to the subtitle file with the generated subtitles embedded. Pass `--no-keep-video` to skip saving a video copy and process audio only. Pass `--keep-audio` to also save the extracted audio file.

The default model is `whisper-large-v3-turbo`. Use `whisper-large-v3` when accuracy is more important than speed. The default temperature is `0.0` (fully deterministic); increase it slightly (e.g. `0.2`) if the transcription feels too repetitive.
