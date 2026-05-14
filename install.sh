#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.video-editor"
BIN_DIR="/usr/local/bin"

echo "=== Video Editor Installer ==="
echo ""

# ── Homebrew ──────────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "→ Installing Homebrew…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        [ -x "$candidate" ] && eval "$($candidate shellenv)" && break
    done
else
    echo "✓ Homebrew"
fi

# ── ffmpeg ────────────────────────────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
    echo "→ Installing ffmpeg…"
    brew install ffmpeg
else
    echo "✓ ffmpeg"
fi

# ── Python 3.10+ ──────────────────────────────────────────────────────────────
PYTHON=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3 || true)
if [ -z "$PYTHON" ] || ! "$PYTHON" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    echo "→ Installing Python 3.12…"
    brew install python@3.12
    PYTHON="$(brew --prefix python@3.12)/bin/python3.12"
else
    echo "✓ Python ($PYTHON)"
fi

# ── Copy app files ────────────────────────────────────────────────────────────
echo "→ Installing to $INSTALL_DIR…"
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/." "$INSTALL_DIR/"

# ── Install launcher ──────────────────────────────────────────────────────────
echo "→ Installing 'video-editor' command…"
sudo tee "$BIN_DIR/video-editor" > /dev/null <<EOF
#!/usr/bin/env bash
exec "$PYTHON" "$INSTALL_DIR/main.py" "\$@"
EOF
sudo chmod +x "$BIN_DIR/video-editor"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Done! Run:"
echo ""
echo "  video-editor --input video.mp4"
echo ""
echo "Voice-triggered cuts (one-time setup):"
echo "  pip install faster-whisper"
echo "  video-editor --input video.mp4 --trigger-phrase \"remove last section\""
