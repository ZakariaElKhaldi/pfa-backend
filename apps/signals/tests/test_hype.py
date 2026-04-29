"""Fade-the-hype guardrail tests (Long 2024)."""

from apps.signals.hype import apply_hype_dampener, compute_mention_rate_z


def test_apply_hype_dampener_below_threshold_returns_original():
    """Z-score below threshold → sentiment unchanged, not dampened."""
    adjusted, dampened = apply_hype_dampener(
        sentiment=0.8, mention_rate_z=1.5, z_threshold=2.0, lambda_=0.5
    )
    assert adjusted == 0.8
    assert dampened is False


def test_compute_mention_rate_z_empty_baseline_returns_zero():
    """No history → z-score 0 (safe no-op, cannot dampen without baseline)."""
    assert compute_mention_rate_z(current_count=50, baseline_counts=[]) == 0.0


def test_compute_mention_rate_z_zero_std_returns_zero():
    """Constant baseline (std=0) → z-score 0, safe no-op."""
    assert compute_mention_rate_z(current_count=50, baseline_counts=[10, 10, 10, 10]) == 0.0


def test_compute_mention_rate_z_spike_returns_positive_z():
    """Current 100 vs baseline mean 10 std 5 → z = (100-10)/5 = 18."""
    z = compute_mention_rate_z(current_count=100, baseline_counts=[5, 10, 15, 10])
    # baseline mean = 10, std (pop) = sqrt(((5-10)^2 + 0 + (15-10)^2 + 0)/4) = sqrt(12.5) ≈ 3.536
    # z = (100-10)/3.536 ≈ 25.46
    assert z > 20.0
    assert z < 30.0


def test_compute_mention_rate_z_normal_level_returns_low_z():
    """Current at baseline mean → z ≈ 0."""
    z = compute_mention_rate_z(current_count=10, baseline_counts=[8, 10, 12, 10])
    assert abs(z) < 1.0


def test_apply_hype_dampener_above_threshold_dampens_by_lambda():
    """Z-score above threshold → sentiment scaled by (1 - lambda)."""
    adjusted, dampened = apply_hype_dampener(
        sentiment=0.8, mention_rate_z=2.5, z_threshold=2.0, lambda_=0.5
    )
    assert adjusted == 0.4  # 0.8 * (1 - 0.5)
    assert dampened is True


def test_apply_hype_dampener_default_params_hype_case():
    """Default lambda=0.5, threshold=2.0."""
    adjusted, dampened = apply_hype_dampener(sentiment=1.0, mention_rate_z=3.0)
    assert adjusted == 0.5
    assert dampened is True


def test_apply_hype_dampener_exactly_at_threshold_does_not_fire():
    """Strictly greater than threshold; equal does not dampen."""
    adjusted, dampened = apply_hype_dampener(
        sentiment=0.8, mention_rate_z=2.0, z_threshold=2.0
    )
    assert adjusted == 0.8
    assert dampened is False
