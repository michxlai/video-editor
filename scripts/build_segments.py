from __future__ import annotations

from dataclasses import dataclass

from scripts.detect_silence import SilenceInterval


@dataclass
class KeepSegment:
    start: float
    end: float
    index: int

    @property
    def duration(self) -> float:
        return self.end - self.start


def build_keep_segments(
    silence_intervals: list[SilenceInterval],
    total_duration: float,
    padding: float = 0.25,
    min_segment_duration: float = 0.1,
    extra_removal_ranges: list[tuple[float, float]] | None = None,
) -> list[KeepSegment]:
    silence_tuples = [(s.start, s.end) for s in silence_intervals]
    if extra_removal_ranges:
        silence_tuples.extend(extra_removal_ranges)
    merged_silence = merge_intervals(silence_tuples)
    speech_tuples = _invert_intervals(merged_silence, total_duration)

    # Expand each speech segment by padding on both sides.
    # Clamp the padded start so it never reaches back into a phrase removal zone.
    phrase_ends = [end for _, end in extra_removal_ranges] if extra_removal_ranges else []
    padded: list[tuple[float, float]] = []
    for start, end in speech_tuples:
        padded_start = max(0.0, start - padding)
        # If padding pulls us before a phrase removal boundary, clamp to that boundary
        for rm_end in phrase_ends:
            if padded_start < rm_end <= start:
                padded_start = rm_end
        padded.append((padded_start, min(total_duration, end + padding)))

    merged_speech = merge_intervals(padded)

    segments = []
    for i, (start, end) in enumerate(merged_speech):
        if end - start >= min_segment_duration:
            segments.append(KeepSegment(start=start, end=end, index=i))

    return segments


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not intervals:
        return []
    sorted_ivs = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_ivs[0]]
    for start, end in sorted_ivs[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _invert_intervals(
    silence: list[tuple[float, float]],
    total_duration: float,
) -> list[tuple[float, float]]:
    if not silence:
        return [(0.0, total_duration)]

    keep: list[tuple[float, float]] = []
    cursor = 0.0

    for start, end in silence:
        if cursor < start:
            keep.append((cursor, start))
        cursor = max(cursor, end)

    if cursor < total_duration:
        keep.append((cursor, total_duration))

    return keep
