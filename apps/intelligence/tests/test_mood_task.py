"""Hourly mood snapshot task tests."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.intelligence.models import MarketMoodSnapshot
from apps.intelligence.tasks import compute_mood_snapshots_all
from apps.social.models import SocialPost
from apps.tickers.models import Ticker, Watchlist


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="u", email="u@x.com", password="p"
    )


@pytest.mark.django_db
def test_compute_mood_snapshots_all_runs_for_watched_tickers(user):
    ticker = Ticker.objects.create(symbol="AAPL", name="Apple")
    Watchlist.objects.create(user=user, ticker=ticker)
    now = timezone.now()
    for i in range(5):
        SocialPost.objects.create(
            ticker=ticker, source="reddit", external_id=f"p{i}",
            content="x", cleaned_text="x",
            sentiment_score=0.5, sentiment_label="bullish",
            posted_at=now - timedelta(minutes=i * 10),
        )
    count = compute_mood_snapshots_all()
    assert count == 1
    assert MarketMoodSnapshot.objects.filter(ticker=ticker).count() == 1


@pytest.mark.django_db
def test_compute_mood_snapshots_all_skips_unwatched():
    Ticker.objects.create(symbol="MSFT", name="Microsoft")
    count = compute_mood_snapshots_all()
    assert count == 0
    assert MarketMoodSnapshot.objects.count() == 0
