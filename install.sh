#!/usr/bin/env bash
set -euo pipefail

error() { echo "ERROR: $*" >&2; exit 1; }

# Check Python >= 3.10
if ! command -v python3 &>/dev/null; then
    error "python3 not found. Install Python 3.10 or newer and try again."
fi

py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
py_major=$(echo "$py_version" | cut -d. -f1)
py_minor=$(echo "$py_version" | cut -d. -f2)

if [[ "$py_major" -lt 3 || ( "$py_major" -eq 3 && "$py_minor" -lt 10 ) ]]; then
    error "Python 3.10+ is required (found $py_version). Install a newer Python and try again."
fi

echo "Using Python $py_version"

# Check ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    error "ffmpeg not found. Install it first (e.g. 'brew install ffmpeg') and try again."
fi

# Install pipx if missing
if ! command -v pipx &>/dev/null; then
    echo "Installing pipx..."
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    export PATH="$PATH:$HOME/.local/bin"
fi

# Install the package
echo "Installing yt-dlp-subs..."
if pipx list 2>/dev/null | grep -q "yt-dlp-subs"; then
    pipx reinstall yt-dlp-subs --python "$(command -v python3)"
else
    pipx install "$(dirname "$0")" --python "$(command -v python3)"
fi

echo ""
echo "Done! Run 'yt-dlp-subs --help' to get started."
echo "If the command is not found, open a new terminal or run: source ~/.zshrc"
