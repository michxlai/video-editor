from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Callable

from scripts.build_segments import build_keep_segments
from scripts.cut_merge import cut_and_merge
from scripts.detect_silence import detect_silence
from scripts.logger import log_step, setup_logger
from scripts.probe import probe_file

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".mts", ".ts"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Remove pauses from video files.")
    p.add_argument("--input", required=True, type=Path, help="Source video file")
    p.add_argument("--output", type=Path, default=None, help="Output path (default: executions/<name>_no_pauses.<ext>)")
    p.add_argument("--silence-threshold-db", type=float, default=-30.0, dest="noise_db")
    p.add_argument("--min-pause-duration", type=float, default=2.0, dest="min_pause")
    p.add_argument("--padding", type=float, default=0.40, help="Seconds to keep around speech edges")
    p.add_argument("--tmp-dir", type=Path, default=Path(".tmp"), dest="tmp_dir")
    p.add_argument("--log-file", type=Path, default=Path(".tmp/logs.txt"), dest="log_file")
    p.add_argument("--keep-tmp", action="store_true", dest="keep_tmp")
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument(
        "--trigger-phrase",
        type=str,
        default=None,
        dest="trigger_phrase",
        help='Spoken phrase that removes the preceding segment (e.g. "cut last part")',
    )
    p.add_argument(
        "--model",
        type=str,
        default="small",
        dest="whisper_model",
        help="Whisper model: tiny, base, small, medium, large-v3 (default: small)",
    )
    p.add_argument(
        "--language",
        type=str,
        default=None,
        dest="whisper_language",
        help="Language code for transcription, e.g. en, de, fr (default: auto-detect)",
    )
    p.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.45,
        dest="fuzzy_threshold",
        help="Per-token similarity threshold 0.0–1.0 (default: 0.45)",
    )
    return p.parse_args()


def validate_inputs(args: argparse.Namespace) -> None:
    if not args.input.exists():
        sys.exit(f"[ERROR] Input file not found: {args.input}")
    if args.input.suffix.lower() not in SUPPORTED_EXTENSIONS:
        sys.exit(f"[ERROR] Unsupported extension '{args.input.suffix}'. Supported: {SUPPORTED_EXTENSIONS}")
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            sys.exit(
                f"[ERROR] '{binary}' not found on PATH.\n"
                "  Install: brew install ffmpeg  (macOS)  |  apt install ffmpeg  (Linux)"
            )
    if args.trigger_phrase:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            sys.exit(
                "[ERROR] faster-whisper is required for --trigger-phrase.\n"
                "  Install: pip install faster-whisper"
            )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)


def run_with_retry(
    fn: Callable,
    args: tuple,
    kwargs: dict,
    max_retries: int = 2,
    step_name: str = "",
    logger=None,
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            correction = f"retry {attempt + 1}/{max_retries}" if attempt < max_retries else "exhausted"
            log_step(logger, step_name, "FAIL", str(exc)[:300], correction)
            if attempt < max_retries:
                time.sleep(1)
    raise last_exc


def main() -> None:
    args = parse_args()
    validate_inputs(args)

    args.tmp_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(args.log_file)

    executions_dir = Path("executions")
    executions_dir.mkdir(exist_ok=True)

    output_path = args.output or (
        executions_dir / f"{args.input.stem}_no_pauses{args.input.suffix}"
    )

    log_step(logger, "main", "START", f"input={args.input} output={output_path}")

    # Stage 1: probe
    log_step(logger, "probe", "START", str(args.input))
    probe = probe_file(args.input)
    log_step(logger, "probe", "SUCCESS", f"codec={probe.video.codec_name} duration={probe.duration:.2f}s")

    # Stage 2: detect silence
    log_step(logger, "detect_silence", "START", f"noise={args.noise_db}dB min_dur={args.min_pause}s")

    def _detect():
        return detect_silence(
            args.input,
            noise_db=args.noise_db,
            min_duration=args.min_pause,
            total_duration=probe.duration,
            logger=logger,
        )

    silences = run_with_retry(_detect, (), {}, step_name="detect_silence", logger=logger)
    log_step(logger, "detect_silence", "SUCCESS", f"{len(silences)} silence interval(s) found")

    # Stage 2b/2c: phrase-triggered cuts (optional)
    extra_removal_ranges: list[tuple[float, float]] | None = None
    if args.trigger_phrase:
        from scripts.phrase_cuts import build_phrase_removal_ranges, find_phrase_matches
        from scripts.transcribe import transcribe

        log_step(logger, "transcribe", "START", f"model={args.whisper_model} phrase='{args.trigger_phrase}'")
        words = run_with_retry(
            transcribe,
            (args.input,),
            {"model_name": args.whisper_model, "language": args.whisper_language, "logger": logger},
            step_name="transcribe",
            logger=logger,
        )
        log_step(logger, "transcribe", "SUCCESS", f"{len(words)} word(s) transcribed")

        matches = find_phrase_matches(words, args.trigger_phrase, fuzzy_threshold=args.fuzzy_threshold)
        log_step(logger, "phrase_cuts", "INFO", f"{len(matches)} trigger phrase match(es) found")
        for m in matches:
            log_step(logger, "phrase_cuts", "INFO", f"  match at {m.phrase_start:.2f}s → {m.phrase_end:.2f}s")

        extra_removal_ranges = build_phrase_removal_ranges(matches, silences, probe.duration, padding=args.padding)
        log_step(logger, "phrase_cuts", "SUCCESS", f"{len(extra_removal_ranges)} removal range(s) computed")
        for start, end in extra_removal_ranges:
            log_step(logger, "phrase_cuts", "INFO", f"  remove {start:.2f}s → {end:.2f}s")

    # Stage 3: build keep-segments
    segments = build_keep_segments(
        silences,
        probe.duration,
        padding=args.padding,
        extra_removal_ranges=extra_removal_ranges,
    )
    log_step(logger, "build_segments", "SUCCESS", f"{len(segments)} keep segment(s)")

    if args.dry_run:
        print(f"\n{'─'*60}")
        print(f"DRY RUN — {len(segments)} segment(s) to keep:")
        total_kept = 0.0
        for seg in segments:
            print(f"  [{seg.index:3d}] {seg.start:8.3f}s → {seg.end:8.3f}s  ({seg.duration:.3f}s)")
            total_kept += seg.duration
        removed = probe.duration - total_kept
        print(f"\n  Source duration : {probe.duration:.2f}s")
        print(f"  Output duration : {total_kept:.2f}s")
        print(f"  Removed         : {removed:.2f}s ({100*removed/probe.duration:.1f}%)")
        print(f"{'─'*60}\n")
        return

    if not segments:
        log_step(logger, "main", "SUCCESS", "No speech found — copying input to output unchanged")
        shutil.copy2(args.input, output_path)
        print(f"Output: {output_path}")
        return

    if len(segments) == 1 and segments[0].start == 0.0 and segments[0].end >= probe.duration - 0.1:
        log_step(logger, "main", "SUCCESS", "No pauses found — copying input to output unchanged")
        shutil.copy2(args.input, output_path)
        print(f"Output: {output_path}")
        return

    # Stage 4: cut and merge
    log_step(logger, "cut_merge", "START", f"{len(segments)} segments → {output_path}")

    def _cut(genpts=False):
        return cut_and_merge(args.input, segments, output_path, probe, args.tmp_dir, logger, genpts=genpts)

    def _cut_with_fallback():
        try:
            return _cut(genpts=False)
        except RuntimeError as exc:
            stderr = str(exc)
            if "DTS" in stderr or "non monotonous" in stderr or "non-monotonous" in stderr:
                log_step(logger, "cut_merge", "FAIL", "DTS discontinuity detected", "retrying with -fflags +genpts")
                return _cut(genpts=True)
            if "encoder" in stderr.lower() or "codec" in stderr.lower():
                log_step(logger, "cut_merge", "FAIL", "codec error", "falling back to libx264/aac")
                _patch_probe_for_fallback(probe)
                return _cut(genpts=False)
            raise

    run_with_retry(_cut_with_fallback, (), {}, step_name="cut_merge", logger=logger)
    log_step(logger, "cut_merge", "SUCCESS", str(output_path))

    # Cleanup
    if not args.keep_tmp:
        seg_dir = args.tmp_dir / "segments"
        if seg_dir.exists():
            shutil.rmtree(seg_dir)

    log_step(logger, "main", "SUCCESS", f"Output: {output_path}")
    print(f"\nOutput: {output_path}")


def _patch_probe_for_fallback(probe) -> None:
    probe.video.codec_name = "h264"
    probe.audio.audio_codec = "aac"
    probe.audio.codec_name = "aac"


if __name__ == "__main__":
    main()
