$ErrorActionPreference = "Stop"

function Error($msg) { Write-Error "ERROR: $msg"; exit 1 }

# Check Python >= 3.10
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Error "py not found. Install Python 3.10 or newer from https://python.org and try again."
}

$version = py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major, $minor = $version.Split('.') | ForEach-Object { [int]$_ }

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
    Error "Python 3.10+ is required (found $version). Install a newer Python and try again."
}

Write-Host "Using Python $version"

# Check ffmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Error "ffmpeg not found. Install it first (e.g. 'winget install Gyan.FFmpeg') and try again."
}

# Install pipx if missing
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "Installing pipx..."
    py -m pip install --user pipx
    py -m pipx ensurepath
    $env:PATH += ";$env:APPDATA\Python\Scripts"
}

# Install the package
Write-Host "Installing yt-dlp-subs..."
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = (Get-Command py).Source
pipx install $scriptDir --python $pythonPath --force

Write-Host ""
Write-Host "Done! Run 'yt-dlp-subs --help' to get started."
Write-Host "If the command is not found, open a new terminal."
