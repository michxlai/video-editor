# pause-remover

Removes pauses longer than 2 seconds from video files. Outputs the same format, codec, resolution, and audio settings as the source.

## Requirements

```bash
brew install ffmpeg   # macOS
# apt install ffmpeg  # Linux
```

No Python packages required (stdlib only, Python 3.10+).

## Usage

```bash
cd pause-remover

# Basic — output lands in executions/
python3 main.py --input /path/to/video.mp4

# Custom output path
python3 main.py --input video.mp4 --output executions/clean.mp4

# Preview what will be cut (no files written)
python3 main.py --input video.mp4 --dry-run

# Tune silence threshold (louder room → raise threshold, e.g. -25)
python3 main.py --input video.mp4 --silence-threshold-db -25

# Only cut pauses longer than 3 seconds
python3 main.py --input video.mp4 --min-pause-duration 3.0

# Keep temporary segment files for inspection
python3 main.py --input video.mp4 --keep-tmp
```

## Arguments

| Flag | Default | Description |
|---|---|---|
| `--input` | required | Source video file |
| `--output` | `executions/<name>_no_pauses.<ext>` | Output path |
| `--silence-threshold-db` | `-30` | Noise floor in dB. Lower = stricter silence detection |
| `--min-pause-duration` | `2.0` | Minimum pause length (seconds) to remove |
| `--padding` | `0.25` | Seconds to keep around speech edges (prevents word clipping) |
| `--dry-run` | — | Print cut plan without processing |
| `--keep-tmp` | — | Retain `.tmp/segments/` after completion |

## Supported formats

mp4, mov, mkv, avi, webm, m4v, mts, ts

## Output

- Same container format as input
- Same video codec (h264, hevc, vp9, av1, prores, dnxhd)
- Same resolution and frame rate
- Same audio codec (aac, mp3, opus, pcm, flac, ac3)
- Logs written to `.tmp/logs.txt`
