#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/michxlai/video-editor.git"
INSTALL_DIR="$HOME/video-editor"
BIN_DIR="/usr/local/bin"

# ── Homebrew ──────────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "→ Installing Homebrew…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        [ -x "$candidate" ] && eval "$($candidate shellenv)" && break
    done
fi

# ── ffmpeg ────────────────────────────────────────────────────────────────────
if ! command -v ffmpeg &>/dev/null; then
    echo "→ Installing ffmpeg…"
    brew install ffmpeg
fi

# ── Python 3.10+ ──────────────────────────────────────────────────────────────
PYTHON=$(command -v python3.12 || command -v python3.11 || command -v python3.10 || command -v python3 || true)
if [ -z "$PYTHON" ] || ! "$PYTHON" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    echo "→ Installing Python 3.12…"
    brew install python@3.12
    PYTHON="$(brew --prefix python@3.12)/bin/python3.12"
fi

# ── Clone / update repo ───────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "→ Updating video-editor…"
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "→ Cloning video-editor…"
    git clone "$REPO" "$INSTALL_DIR"
fi

# ── Install launcher ──────────────────────────────────────────────────────────
LAUNCHER="$BIN_DIR/video-editor"
echo "→ Installing 'video-editor' command…"
sudo tee "$LAUNCHER" > /dev/null <<EOF
#!/usr/bin/env bash
exec "$PYTHON" "$INSTALL_DIR/pause-remover/main.py" "\$@"
EOF
sudo chmod +x "$LAUNCHER"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Done. Usage:"
echo ""
echo "  video-editor --input video.mp4"
echo ""
echo "Voice-triggered cuts (one-time setup):"
echo "  pip install faster-whisper"
echo "  video-editor --input video.mp4 --trigger-phrase \"remove last section\""
