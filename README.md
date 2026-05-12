# Video Editor

Automatically clean up your recordings in one command. Two modes:

1. **Pause removal** — silences longer than a threshold are cut out automatically
2. **Voice-triggered cuts** — say a phrase like *"remove last section"* while recording; the tool transcribes your audio with Whisper and removes everything from the last pause up to that phrase, including the phrase itself

No manual editing. No timeline scrubbing.

---

## Mac App (no setup required)

Download **PauseRemover-mac-arm64.zip** from the [latest release](https://github.com/michxlai/video-editor/releases/latest), unzip, and open.

> **First launch:** macOS blocks unsigned apps. Right-click `Video Editor.app` → **Open** → **Open**.

---

## CLI (advanced)

### Requirements

```bash
brew install ffmpeg   # macOS
# apt install ffmpeg  # Linux
```

Python 3.10+. No pip packages needed for basic use.

### Basic usage

```bash
# Remove pauses — output saved to executions/
python3 main.py --input video.mp4

# Custom output path
python3 main.py --input video.mp4 --output clean.mp4

# Preview cuts without processing
python3 main.py --input video.mp4 --dry-run
```

### Voice-triggered section removal

While recording, say your trigger phrase (e.g. *"remove last section"*) whenever you want to discard what you just said. The tool finds every occurrence and cuts from the last pause before it up to the phrase itself.

```bash
# Requires: pip install faster-whisper
python3 main.py --input video.mp4 --trigger-phrase "remove last section"

# Use a different Whisper model (tiny/base/small/medium/large-v3)
python3 main.py --input video.mp4 --trigger-phrase "remove last section" --model medium

# Specify language to skip auto-detection
python3 main.py --input video.mp4 --trigger-phrase "remove last section" --language en
```

---

## All arguments

| Flag | Default | Description |
|---|---|---|
| `--input` | required | Source video file |
| `--output` | `executions/<name>_no_pauses.<ext>` | Output path |
| `--silence-threshold-db` | `-30` | Noise floor in dB (lower = stricter) |
| `--min-pause-duration` | `2.0` | Minimum pause length in seconds to cut |
| `--padding` | `0.40` | Seconds to keep around speech edges |
| `--trigger-phrase` | — | Spoken phrase that removes the preceding section |
| `--model` | `small` | Whisper model: tiny, base, small, medium, large-v3 |
| `--language` | auto | Language code for transcription (e.g. `en`, `de`, `fr`) |
| `--fuzzy-threshold` | `0.45` | Per-token similarity for phrase matching (0–1) |
| `--dry-run` | — | Print cut plan, no files written |
| `--keep-tmp` | — | Retain `.tmp/segments/` after completion |

---

## Supported formats

mp4, mov, mkv, avi, webm, m4v, mts, ts

## Output

- Same container, codec, resolution, and frame rate as source
- Supports h264, hevc, vp9, av1, prores, dnxhd (video) and aac, mp3, opus, flac, ac3 (audio)
- Logs written to `.tmp/logs.txt`
