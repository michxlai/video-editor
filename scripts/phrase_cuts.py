from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from scripts.detect_silence import SilenceInterval
from scripts.transcribe import TimedWord


@dataclass
class PhraseMatch:
    phrase_start: float
    phrase_end: float
    word_indices: list[int] = field(default_factory=list)


def find_phrase_matches(
    words: list[TimedWord],
    trigger_phrase: str,
    fuzzy_threshold: float = 0.45,
    allow_token_slack: bool = True,
) -> list[PhraseMatch]:
    trigger_tokens = _normalize(trigger_phrase).split()
    n = len(trigger_tokens)
    if n == 0:
        return []

    candidates: list[tuple[float, PhraseMatch]] = []

    window_sizes = [n]
    if allow_token_slack and n > 1:
        window_sizes += [n - 1, n + 1]

    for w_size in window_sizes:
        slack_threshold = fuzzy_threshold if w_size == n else fuzzy_threshold - 0.05
        for i in range(len(words) - w_size + 1):
            window = words[i : i + w_size]
            window_tokens = [_normalize(w.word) for w in window]
            score = _match_score(trigger_tokens, window_tokens)
            if score >= slack_threshold:
                match = PhraseMatch(
                    phrase_start=window[0].start,
                    phrase_end=window[-1].end,
                    word_indices=list(range(i, i + w_size)),
                )
                candidates.append((score, match))

    # Non-max suppression: keep highest-scoring non-overlapping matches
    candidates.sort(key=lambda x: (-x[0], x[1].phrase_start))
    kept: list[PhraseMatch] = []
    for _, match in candidates:
        overlaps = any(
            match.phrase_start < k.phrase_end and match.phrase_end > k.phrase_start
            for k in kept
        )
        if not overlaps:
            kept.append(match)

    kept.sort(key=lambda m: m.phrase_start)
    return kept


def build_phrase_removal_ranges(
    matches: list[PhraseMatch],
    silence_intervals: list[SilenceInterval],
    total_duration: float,
    padding: float = 0.40,
) -> list[tuple[float, float]]:
    if not matches:
        return []

    from scripts.build_segments import merge_intervals

    merged_silences = merge_intervals([(s.start, s.end) for s in silence_intervals])
    # Cut boundaries: where the video switches from "removed" back to "kept"
    # That's the end of each silence interval, plus 0.0 as the initial boundary
    cut_boundaries: list[float] = [0.0] + [end for _, end in merged_silences]

    removal_ranges: list[tuple[float, float]] = []
    for match in sorted(matches, key=lambda m: m.phrase_start):
        # Most recent boundary strictly before the phrase starts
        last_cut_end = max(
            (b for b in cut_boundaries if b <= match.phrase_start),
            default=0.0,
        )
        # Extend by padding so the padded kept segment starts at phrase_end, not before it
        range_end = min(match.phrase_end + padding, total_duration)
        removal_ranges.append((last_cut_end, range_end))
        # This phrase's end becomes a new boundary for subsequent matches
        cut_boundaries.append(range_end)

    return removal_ranges


def _normalize(text: str) -> str:
    return text.lower().strip(".,!?;:'\"").strip()


def _match_score(trigger: list[str], window: list[str]) -> float:
    # Per-token average: score each word pair independently, then average.
    # More robust than joined-string matching when Whisper mishears individual words.
    # Align by padding the shorter list with empty strings.
    n = max(len(trigger), len(window))
    t_padded = trigger + [""] * (n - len(trigger))
    w_padded = window + [""] * (n - len(window))
    scores = [
        difflib.SequenceMatcher(None, t, w).ratio()
        for t, w in zip(t_padded, w_padded)
    ]
    return sum(scores) / len(scores) if scores else 0.0
