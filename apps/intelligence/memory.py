"""Market mood snapshots (Saravanos 2025 — rule-based variant)."""

from datetime import timedelta

WINDOW_HOURS = 24
EUPHORIC_SENT = 0.7
PANIC_SENT = -0.7
UNCERTAIN_SENT_ABS = 0.2
UNCERTAIN_CONSISTENCY = 0.3
HIGH_CONSISTENCY = 0.7
DEFAULT_P90 = 100


def classify_mood(sentiment: float, post_count: int, p90: int, consistency: float) -> str:
    if sentiment > EUPHORIC_SENT and post_count > p90 and consistency > HIGH_CONSISTENCY:
        return "euphoric"
    if sentiment < PANIC_SENT and post_count > p90:
        return "panic"
    if abs(sentiment) < UNCERTAIN_SENT_ABS and consistency < UNCERTAIN_CONSISTENCY:
        return "uncertain"
    return "bullish" if sentiment >= 0 else "bearish"


def compute_mood_snapshot(ticker):
    from django.utils import timezone

    from apps.intelligence.models import MarketMoodSnapshot
    from apps.social.models import SocialPost

    now = timezone.now()
    window_start = now - timedelta(hours=WINDOW_HOURS)
    posts = list(
        SocialPost.objects.filter(
            ticker=ticker,
            posted_at__gte=window_start,
            posted_at__lte=now,
            sentiment_score__isnull=False,
        ).values_list("sentiment_score", flat=True)
    )
    if not posts:
        return None

    n = len(posts)
    mean_sent = sum(posts) / n
    mean_abs = sum(abs(s) for s in posts) / n
    sign_alignment = abs(sum(1 if s > 0 else -1 for s in posts)) / n
    consistency = (mean_abs + sign_alignment) / 2.0

    mood = classify_mood(mean_sent, n, DEFAULT_P90, consistency)
    confidence = min(1.0, max(0.0, mean_abs))

    return MarketMoodSnapshot.objects.create(
        ticker=ticker,
        embedding={
            "mean_sentiment": mean_sent,
            "post_count": n,
            "consistency": consistency,
            "mean_abs_sentiment": mean_abs,
        },
        dominant_mood=mood,
        confidence=confidence,
        window_start=window_start,
        window_end=now,
    )
