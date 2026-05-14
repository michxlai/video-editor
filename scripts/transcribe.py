from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TimedWord:
    word: str
    start: float
    end: float
    probability: float


def transcribe(
    input_path: Path,
    model_name: str = "small",
    device: str = "auto",
    compute_type: str = "auto",
    language: str | None = None,
    logger: logging.Logger | None = None,
) -> list[TimedWord]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper is required for --trigger-phrase.\n"
            "  Install: pip install faster-whisper"
        )

    _log(logger, f"Loading Whisper model '{model_name}' (device={device}, compute_type={compute_type})")

    resolved_device = device
    resolved_compute = compute_type
    if device == "auto":
        try:
            import torch
            resolved_device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            resolved_device = "cpu"
    if compute_type == "auto":
        resolved_compute = "float16" if resolved_device != "cpu" else "int8"

    model = WhisperModel(model_name, device=resolved_device, compute_type=resolved_compute)
    _log(logger, f"Transcribing {input_path.name}")

    t0 = time.time()
    segments, _ = model.transcribe(str(input_path), word_timestamps=True, language=language)

    words: list[TimedWord] = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                words.append(TimedWord(
                    word=w.word,
                    start=w.start,
                    end=w.end,
                    probability=w.probability,
                ))

    elapsed = time.time() - t0
    _log(logger, f"Transcription complete: {len(words)} word(s) in {elapsed:.1f}s")
    return words


def _log(logger: logging.Logger | None, msg: str) -> None:
    if logger:
        logger.info(msg)
    else:
        print(msg)
