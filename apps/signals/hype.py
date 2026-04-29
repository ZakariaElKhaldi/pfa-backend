"""Fade-the-hype guardrail (Long 2024)."""

import math


def compute_mention_rate_z(current_count: int, baseline_counts: list[int]) -> float:
    if not baseline_counts:
        return 0.0
    n = len(baseline_counts)
    mean = sum(baseline_counts) / n
    variance = sum((c - mean) ** 2 for c in baseline_counts) / n
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (current_count - mean) / std


def apply_hype_dampener(
    sentiment: float,
    mention_rate_z: float,
    z_threshold: float = 2.0,
    lambda_: float = 0.5,
) -> tuple[float, bool]:
    if mention_rate_z > z_threshold:
        return sentiment * (1.0 - lambda_), True
    return sentiment, False
