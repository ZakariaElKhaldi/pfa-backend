"""Market mood snapshot tests (Saravanos 2025 — rule-based variant)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.intelligence.memory import classify_mood, compute_mood_snapshot
from apps.intelligence.models import MarketMoodSnapshot
from apps.social.models import SocialPost
from apps.tickers.models import Ticker


# --- Pure classifier ---


def test_classify_mood_euphoric():
    """High positive sentiment + high volume + high consistency → euphoric."""
    assert classify_mood(sentiment=0.8, post_count=500, p90=100, consistency=0.8) == "euphoric"


def test_classify_mood_panic():
    """Deep negative sentiment + high volume → panic."""
    assert classify_mood(sentiment=-0.8, post_count=500, p90=100, consistency=0.5) == "panic"


def test_classify_mood_uncertain():
    """Sentiment near zero + low consistency → uncertain."""
    assert classify_mood(sentiment=0.1, post_count=50, p90=100, consistency=0.2) == "uncertain"


def test_classify_mood_bullish():
    """Positive sentiment, no extreme conditions → bullish."""
    assert classify_mood(sentiment=0.4, post_count=50, p90=100, consistency=0.5) == "bullish"


def test_classify_mood_bearish():
    """Negative sentiment, no extreme conditions → bearish."""
    assert classify_mood(sentiment=-0.4, post_count=50, p90=100, consistency=0.5) == "bearish"


# --- Orchestrator ---


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL", name="Apple Inc.")


def seed_posts(ticker, count: int, sentiment: float, within_hours: int = 24):
    now = timezone.now()
    for i in range(count):
        SocialPost.objects.create(
            ticker=ticker,
            source="reddit",
            external_id=f"p{i}",
            content=f"post {i}",
            cleaned_text=f"post {i}",
            sentiment_score=sentiment,
            sentiment_label="bullish" if sentiment > 0 else "bearish",
            posted_at=now - timedelta(minutes=i * 10),
        )


@pytest.mark.django_db
def test_compute_mood_snapshot_creates_row(ticker):
    seed_posts(ticker, count=30, sentiment=0.5)
    snap = compute_mood_snapshot(ticker)
    assert snap is not None
    assert isinstance(snap, MarketMoodSnapshot)
    assert snap.ticker == ticker
    assert snap.dominant_mood in {"bullish", "bearish", "uncertain", "euphoric", "panic"}
    assert 0.0 <= snap.confidence <= 1.0
    assert snap.window_start < snap.window_end


@pytest.mark.django_db
def test_compute_mood_snapshot_returns_none_without_posts(ticker):
    assert compute_mood_snapshot(ticker) is None
    assert MarketMoodSnapshot.objects.count() == 0


@pytest.mark.django_db
def test_compute_mood_snapshot_ignores_posts_outside_window(ticker):
    now = timezone.now()
    SocialPost.objects.create(
        ticker=ticker, source="reddit", external_id="old",
        content="x", cleaned_text="x", sentiment_score=0.9,
        sentiment_label="bullish",
        posted_at=now - timedelta(hours=48),
    )
    assert compute_mood_snapshot(ticker) is None


@pytest.mark.django_db
def test_compute_mood_snapshot_classifies_panic(ticker):
    seed_posts(ticker, count=200, sentiment=-0.85)
    snap = compute_mood_snapshot(ticker)
    assert snap is not None
    assert snap.dominant_mood == "panic"
