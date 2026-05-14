from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from scripts.build_segments import KeepSegment
from scripts.probe import ProbeResult, get_frame_rate_float


def cut_and_merge(
    input_path: Path,
    segments: list[KeepSegment],
    output_path: Path,
    probe_result: ProbeResult,
    tmp_dir: Path,
    logger: logging.Logger | None = None,
    genpts: bool = False,
) -> Path:
    seg_dir = tmp_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    ext = input_path.suffix
    video_args = _derive_video_codec_args(probe_result)
    audio_args = _derive_audio_codec_args(probe_result)

    seg_paths: list[Path] = []
    for seg in segments:
        seg_path = seg_dir / f"seg_{seg.index:04d}{ext}"
        _cut_segment(input_path, seg, seg_path, video_args, audio_args, logger)
        seg_paths.append(seg_path)

    concat_list = tmp_dir / "concat_list.txt"
    _write_concat_list(seg_paths, concat_list)

    concat_cmd = _build_concat_cmd(concat_list, output_path, genpts)
    if logger:
        logger.info(f"concat cmd: {' '.join(concat_cmd)}")
    run_ffmpeg(concat_cmd, logger)

    return output_path


def _cut_segment(
    input_path: Path,
    segment: KeepSegment,
    output_path: Path,
    video_codec_args: list[str],
    audio_codec_args: list[str],
    logger: logging.Logger | None = None,
) -> None:
    cmd = _build_cut_cmd(input_path, segment.start, segment.end, output_path, video_codec_args, audio_codec_args)
    if logger:
        logger.debug(f"cut seg {segment.index}: {segment.start:.3f}s → {segment.end:.3f}s")
    run_ffmpeg(cmd, logger)


def _build_cut_cmd(
    input_path: Path,
    start: float,
    end: float,
    output_path: Path,
    video_codec_args: list[str],
    audio_codec_args: list[str],
) -> list[str]:
    seek_args = [] if start == 0.0 else ["-ss", str(start)]
    return [
        "ffmpeg", "-y",
        *seek_args,
        "-to", str(end),
        "-i", str(input_path),
        *video_codec_args,
        *audio_codec_args,
        "-avoid_negative_ts", "make_zero",
        str(output_path),
    ]


def _build_concat_cmd(
    concat_list_path: Path,
    output_path: Path,
    genpts: bool = False,
) -> list[str]:
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list_path)]
    if genpts:
        cmd += ["-fflags", "+genpts"]
    cmd += ["-c", "copy", str(output_path)]
    return cmd


def _write_concat_list(segment_paths: list[Path], list_path: Path) -> None:
    lines = [f"file '{p.resolve()}'" for p in segment_paths]
    list_path.write_text("\n".join(lines) + "\n")


def _derive_video_codec_args(probe: ProbeResult) -> list[str]:
    codec = probe.video.codec_name.lower()
    pix_fmt = probe.video.pix_fmt or "yuv420p"
    w, h = probe.video.width, probe.video.height

    try:
        fps = get_frame_rate_float(probe.video.r_frame_rate)
    except (ValueError, ZeroDivisionError):
        fps = 30.0

    base = ["-pix_fmt", pix_fmt, "-r", str(fps)]
    if w and h:
        base += ["-vf", f"scale={w}:{h}"]

    if codec == "h264":
        enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    elif codec in ("hevc", "h265"):
        enc = ["-c:v", "libx265", "-preset", "medium", "-crf", "20"]
    elif codec == "vp9":
        enc = ["-c:v", "libvpx-vp9", "-crf", "33", "-b:v", "0"]
    elif codec == "av1":
        enc = ["-c:v", "libaom-av1", "-crf", "30", "-b:v", "0"]
    elif codec == "prores":
        profile = _prores_profile(pix_fmt)
        enc = ["-c:v", "prores_ks", "-profile:v", str(profile)]
    elif codec in ("dnxhd", "dnxhr"):
        bitrate = probe.video.bit_rate
        enc = ["-c:v", "dnxhd"]
        if bitrate:
            enc += ["-b:v", str(bitrate)]
    else:
        enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "18"]

    return enc + base


def _derive_audio_codec_args(probe: ProbeResult) -> list[str]:
    codec = (probe.audio.audio_codec or "").lower()
    sr = probe.audio.sample_rate or 48000
    ch = probe.audio.channels or 2
    bitrate = probe.audio.audio_bit_rate

    base = ["-ar", str(sr), "-ac", str(ch)]

    if codec == "aac":
        br = str(bitrate) if bitrate else "192k"
        enc = ["-c:a", "aac", "-b:a", br]
    elif codec == "mp3":
        br = str(bitrate) if bitrate else "192k"
        enc = ["-c:a", "libmp3lame", "-b:a", br]
    elif codec == "opus":
        br = str(bitrate) if bitrate else "128k"
        enc = ["-c:a", "libopus", "-b:a", br]
    elif codec == "vorbis":
        enc = ["-c:a", "libvorbis", "-q:a", "6"]
    elif codec in ("pcm_s16le", "pcm_s24le", "pcm_f32le"):
        enc = ["-c:a", codec]
    elif codec == "flac":
        enc = ["-c:a", "flac"]
    elif codec == "ac3":
        br = str(bitrate) if bitrate else "384k"
        enc = ["-c:a", "ac3", "-b:a", br]
    elif codec == "eac3":
        br = str(bitrate) if bitrate else "640k"
        enc = ["-c:a", "eac3", "-b:a", br]
    else:
        enc = ["-c:a", "aac", "-b:a", "192k"]

    return enc + base


def _prores_profile(pix_fmt: str) -> int:
    # 0=proxy 1=LT 2=standard 3=HQ 4=4444 5=4444XQ
    if "4444" in pix_fmt:
        return 4
    if "10le" in pix_fmt or "10be" in pix_fmt:
        return 3
    return 2


def run_ffmpeg(
    cmd: list[str],
    logger: logging.Logger | None = None,
) -> subprocess.CompletedProcess:
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    if logger:
        logger.debug(f"ffmpeg finished in {elapsed:.1f}s (rc={result.returncode})")
    if result.returncode != 0:
        if logger:
            logger.error(f"ffmpeg stderr: {result.stderr[-2000:]}")
        raise RuntimeError(
            f"ffmpeg failed (rc={result.returncode}): {result.stderr[-500:]}"
        )
    return result
