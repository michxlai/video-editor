from __future__ import annotations

import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from scripts.build_segments import build_keep_segments
from scripts.cut_merge import cut_and_merge
from scripts.detect_silence import detect_silence
from scripts.probe import probe_file


@dataclass
class ProcessConfig:
    input_path: Path
    output_path: Path
    noise_db: float = -30.0
    min_pause: float = 2.0
    padding: float = 0.40


def process_video(
    config: ProcessConfig,
    log_callback: Callable[[str], None] | None = None,
) -> Path:
    def emit(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    tmp_dir = Path(tempfile.mkdtemp(prefix="pause_remover_"))
    try:
        emit(f"Probing {config.input_path.name}…")
        probe = probe_file(config.input_path)
        emit(f"  codec={probe.video.codec_name}  duration={probe.duration:.2f}s")

        emit(f"Detecting silence  (threshold={config.noise_db}dB  min={config.min_pause}s)…")
        silences = detect_silence(
            config.input_path,
            noise_db=config.noise_db,
            min_duration=config.min_pause,
            total_duration=probe.duration,
        )
        emit(f"  {len(silences)} silence interval(s) found")

        segments = build_keep_segments(silences, probe.duration, padding=config.padding)
        emit(f"  {len(segments)} keep segment(s)")

        if not segments:
            emit("No speech detected — copying input unchanged")
            shutil.copy2(config.input_path, config.output_path)
            return config.output_path

        if (
            len(segments) == 1
            and segments[0].start == 0.0
            and segments[0].end >= probe.duration - 0.1
        ):
            emit("No pauses found — copying input unchanged")
            shutil.copy2(config.input_path, config.output_path)
            return config.output_path

        emit(f"Cutting and merging {len(segments)} segment(s)…")

        def _cut(genpts: bool = False) -> None:
            cut_and_merge(
                config.input_path, segments, config.output_path, probe, tmp_dir,
                genpts=genpts,
            )

        def _cut_with_fallback() -> None:
            try:
                _cut(genpts=False)
            except RuntimeError as exc:
                stderr = str(exc)
                if "DTS" in stderr or "non monotonous" in stderr or "non-monotonous" in stderr:
                    emit("  DTS discontinuity — retrying with -fflags +genpts")
                    _cut(genpts=True)
                elif "encoder" in stderr.lower() or "codec" in stderr.lower():
                    emit("  Codec error — falling back to h264/aac")
                    probe.video.codec_name = "h264"
                    probe.audio.audio_codec = "aac"
                    probe.audio.codec_name = "aac"
                    _cut(genpts=False)
                else:
                    raise

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                _cut_with_fallback()
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                emit(f"  Attempt {attempt + 1} failed: {exc}")
                if attempt < 2:
                    time.sleep(1)
        if last_exc is not None:
            raise last_exc

        emit("Done!")
        return config.output_path

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
