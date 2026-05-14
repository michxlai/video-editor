from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StreamInfo:
    codec_name: str
    codec_type: str
    width: int | None
    height: int | None
    r_frame_rate: str
    bit_rate: int | None
    pix_fmt: str | None
    sample_rate: int | None
    channel_layout: str | None
    channels: int | None
    audio_codec: str | None
    audio_bit_rate: int | None


@dataclass
class ProbeResult:
    video: StreamInfo
    audio: StreamInfo
    duration: float
    container_format: str
    file_path: Path


def probe_file(file_path: Path) -> ProbeResult:
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    data = json.loads(result.stdout)

    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        raise ValueError(f"No video stream found in {file_path}")
    if not audio_stream:
        raise ValueError(f"No audio stream found in {file_path}")

    def _int_or_none(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    video = StreamInfo(
        codec_name=video_stream.get("codec_name", ""),
        codec_type="video",
        width=_int_or_none(video_stream.get("width")),
        height=_int_or_none(video_stream.get("height")),
        r_frame_rate=video_stream.get("r_frame_rate", "30/1"),
        bit_rate=_int_or_none(video_stream.get("bit_rate")),
        pix_fmt=video_stream.get("pix_fmt"),
        sample_rate=None,
        channel_layout=None,
        channels=None,
        audio_codec=None,
        audio_bit_rate=None,
    )

    audio = StreamInfo(
        codec_name=audio_stream.get("codec_name", ""),
        codec_type="audio",
        width=None,
        height=None,
        r_frame_rate="",
        bit_rate=None,
        pix_fmt=None,
        sample_rate=_int_or_none(audio_stream.get("sample_rate")),
        channel_layout=audio_stream.get("channel_layout"),
        channels=_int_or_none(audio_stream.get("channels")),
        audio_codec=audio_stream.get("codec_name"),
        audio_bit_rate=_int_or_none(audio_stream.get("bit_rate")),
    )

    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))
    container_format = fmt.get("format_name", "")

    return ProbeResult(
        video=video,
        audio=audio,
        duration=duration,
        container_format=container_format,
        file_path=file_path,
    )


def get_frame_rate_float(r_frame_rate: str) -> float:
    parts = r_frame_rate.split("/")
    if len(parts) == 2:
        num, den = int(parts[0]), int(parts[1])
        if den == 0:
            raise ValueError(f"Invalid frame rate: {r_frame_rate}")
        return num / den
    return float(r_frame_rate)
