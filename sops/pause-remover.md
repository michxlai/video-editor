# SOP: pause-remover

## Setup

1. Install ffmpeg: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux)
2. Python 3.10+ required (uses `int | None` union syntax)
3. No pip install needed

## Run Command

```bash
cd /path/to/pause-remover
python3 main.py --input video.mp4
```

Output appears in `executions/video_no_pauses.mp4`.

## Expected I/O

- **Input**: any video with audio (mp4, mov, mkv, avi, webm, m4v, mts, ts)
- **Output**: same container/codec/resolution, pauses >2s removed
- **Logs**: `.tmp/logs.txt` — one structured line per step

## Tuning Guide

| Symptom | Fix |
|---|---|
| Words get clipped at start/end | Increase `--padding` (e.g. `0.4`) |
| Background noise treated as speech | Lower `--silence-threshold-db` (e.g. `-25`) |
| Short hesitations being removed | Increase `--min-pause-duration` (e.g. `3.0`) |
| Genuine pauses not removed | Raise `--silence-threshold-db` (e.g. `-35`) |

## Troubleshooting

**`ffmpeg not found`**
```bash
brew install ffmpeg
```

**`No video stream found`**
The file may be audio-only or corrupted. Verify with `ffprobe -i file.mp4`.

**DTS discontinuity in concat step**
Handled automatically (retries with `-fflags +genpts`). If it persists, check `.tmp/logs.txt` for the exact ffmpeg error.

**Codec error on cut**
Handled automatically (falls back to libx264/aac). Output quality may differ slightly from source.

**Output is empty / zero duration**
All detected segments were below `min_segment_duration` (100ms). Use `--dry-run` to inspect the cut plan and adjust `--silence-threshold-db`.

**Disk full during processing**
Temporary segments are written to `.tmp/segments/`. Ensure sufficient space (~2-3× source file size during processing).

## Extending

- **New codec support**: add a mapping in `scripts/cut_merge.py` → `_derive_video_codec_args`
- **Different silence detection**: swap `scripts/detect_silence.py` with a VAD-based implementation (e.g. WebRTC VAD) while keeping the `SilenceInterval` return type
- **Batch processing**: wrap `main.py` call in a shell loop or add a `--input-dir` argument
