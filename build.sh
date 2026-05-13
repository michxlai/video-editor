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
PYTHON=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || echo "python3")
PIP="$PYTHON -m pip"
$PIP install pyinstaller --quiet

echo "=== Building .app ==="
$PYTHON -m PyInstaller pause_remover.spec --noconfirm

APP="dist/Video Editor.app"
DMG="dist/VideoEditor-mac.dmg"
VOL="Video Editor"

echo "=== Building DMG ==="
rm -f "$DMG"

# Temp staging folder
STAGING=$(mktemp -d)
cp -r "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

# Create DMG
hdiutil create \
    -volname "$VOL" \
    -srcfolder "$STAGING" \
    -ov -format UDZO \
    "$DMG"

rm -rf "$STAGING"

echo ""
echo "=== Done ==="
echo "DMG: $DMG"
