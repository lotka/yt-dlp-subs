# yt-dlp-subs

Command line subtitle generation for online videos. It uses `yt-dlp` to extract audio and Groq's Whisper transcription endpoint to produce an `.srt` subtitle file.

## Install

### macOS

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

Install Python and set up the project:

```bash
pyenv install 3.11.11
pyenv local 3.11.11
pyenv exec python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

### Linux (Ubuntu / Debian)

Install build dependencies and ffmpeg:

```bash
sudo apt update
sudo apt install -y ffmpeg curl git build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev libncursesw5-dev \
  xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
```

Install pyenv:

```bash
curl https://pyenv.run | bash
```

Add pyenv to your shell (`~/.bashrc` or `~/.zshrc`):

```bash
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc
```

Install Python and set up the project:

```bash
pyenv install 3.11.11
pyenv local 3.11.11
pyenv exec python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

### Windows

1. Install [ffmpeg](https://ffmpeg.org/download.html) and add it to your `PATH`.
2. Install [pyenv-win](https://github.com/pyenv-win/pyenv-win) via PowerShell (run as Administrator):

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
```

Restart your terminal, then:

```powershell
pyenv install 3.11.11
pyenv local 3.11.11
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

---

> Run `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows) every time you open a new terminal in this project.

## Usage

```bash
yt-dlp-subs "https://www.youtube.com/watch?v=d0b6ECKU_Os" --groq-api-key="$GROQ_API_KEY"
```

You can also set the API key once:

```bash
export GROQ_API_KEY="gsk_..."
yt-dlp-subs "https://www.youtube.com/watch?v=d0b6ECKU_Os"
```

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
