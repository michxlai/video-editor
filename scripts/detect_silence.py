from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SilenceInterval:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


_START_RE = re.compile(r"silence_start:\s*([\d.]+)")
_END_RE = re.compile(r"silence_end:\s*([\d.]+)")


def detect_silence(
    input_path: Path,
    noise_db: float = -30.0,
    min_duration: float = 2.0,
    total_duration: float | None = None,
    logger: logging.Logger | None = None,
) -> list[SilenceInterval]:
    cmd = _build_ffmpeg_cmd(input_path, noise_db, min_duration)
    if logger:
        logger.debug(f"detect_silence cmd: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    # silencedetect writes to stderr; non-zero return is expected with -f null
    intervals = _parse_silence_output(result.stderr, total_duration, logger)
    if logger:
        logger.info(f"detect_silence: found {len(intervals)} silence interval(s)")
    return intervals


def _build_ffmpeg_cmd(
    input_path: Path,
    noise_db: float,
    min_duration: float,
) -> list[str]:
    return [
        "ffmpeg", "-i", str(input_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-vn", "-f", "null", "-",
    ]


def _parse_silence_output(
    stderr_text: str,
    total_duration: float | None = None,
    logger: logging.Logger | None = None,
) -> list[SilenceInterval]:
    intervals: list[SilenceInterval] = []
    pending_start: float | None = None

    for line in stderr_text.splitlines():
        start_match = _START_RE.search(line)
        end_match = _END_RE.search(line)

        if start_match:
            pending_start = float(start_match.group(1))

        if end_match and pending_start is not None:
            end = float(end_match.group(1))
            intervals.append(SilenceInterval(start=pending_start, end=end))
            pending_start = None

    # Trailing silence: file ends while still in silence
    if pending_start is not None:
        if total_duration is not None:
            intervals.append(SilenceInterval(start=pending_start, end=total_duration))
            if logger:
                logger.warning(
                    f"detect_silence: trailing silence from {pending_start}s "
                    f"clamped to file end {total_duration}s"
                )
        else:
            if logger:
                logger.warning(
                    f"detect_silence: unpaired silence_start at {pending_start}s discarded"
                )

    return intervals
