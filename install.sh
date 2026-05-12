#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/michxlai/video-editor.git"
INSTALL_DIR="$HOME/video-editor"

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
if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
    echo "→ Installing Python 3.12…"
    brew install python@3.12
fi

# ── Clone / update repo ───────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "→ Updating video-editor…"
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "→ Cloning video-editor…"
    git clone "$REPO" "$INSTALL_DIR"
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Done. Run it:"
echo ""
echo "  python3 $INSTALL_DIR/pause-remover/main.py --input video.mp4"
echo ""
echo "Voice-triggered cuts (install faster-whisper first):"
echo "  pip install faster-whisper"
echo "  python3 $INSTALL_DIR/pause-remover/main.py --input video.mp4 --trigger-phrase \"remove last section\""
