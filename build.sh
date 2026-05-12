#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Checking dependencies ==="
if [ ! -f bin/ffmpeg ] || [ ! -f bin/ffprobe ]; then
    echo "Downloading static ffmpeg/ffprobe..."
    mkdir -p bin
    curl -L "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip" -o /tmp/ffmpeg.zip
    curl -L "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip" -o /tmp/ffprobe.zip
    unzip -o /tmp/ffmpeg.zip -d bin
    unzip -o /tmp/ffprobe.zip -d bin
    chmod +x bin/ffmpeg bin/ffprobe
fi

echo "=== Installing PyInstaller ==="
pip install pyinstaller --quiet

echo "=== Building .app ==="
pyinstaller pause_remover.spec --noconfirm

echo ""
echo "=== Done ==="
echo "App: dist/PauseRemover.app"
echo ""
echo "To zip for distribution:"
echo "  cd dist && zip -r PauseRemover-mac.zip PauseRemover.app"
