from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.market.models import PriceSnapshot
from apps.signals.features import build_feature_vector
from apps.social.models import SocialPost
from apps.tickers.models import Ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL")


def make_price_history(ticker, count=30, base_price=150.0):
    now = timezone.now()
    for i in range(count):
        price = base_price + i * 0.5
        PriceSnapshot.objects.create(
            ticker=ticker,
            price=Decimal(str(price)),
            open_price=Decimal(str(price - 0.3)),
            high_price=Decimal(str(price + 0.5)),
            low_price=Decimal(str(price - 0.5)),
            volume=1000000 + i * 10000,
            timestamp=now - timedelta(days=count - i),
        )


def make_scored_posts(ticker, count=10):
    now = timezone.now()
    for i in range(count):
        SocialPost.objects.create(
            ticker=ticker,
            source=SocialPost.SOURCE_STOCKTWITS,
            external_id=f"feat_{i}",
            content="test post content",
            cleaned_text="test post content",
            sentiment_score=0.3 + (i % 3) * 0.2,
            sentiment_label="bullish",
            positive_prob=0.6 + (i % 3) * 0.1,
            negative_prob=0.1,
            neutral_prob=0.3 - (i % 3) * 0.1,
            posted_at=now - timedelta(minutes=i * 2),
            fetched_at=now - timedelta(minutes=i * 2),
        )


@pytest.mark.django_db
def test_build_feature_vector_returns_dict(ticker):
    make_price_history(ticker)
    make_scored_posts(ticker)
    vector = build_feature_vector("AAPL")
    assert isinstance(vector, dict)
    assert len(vector) > 0


@pytest.mark.django_db
def test_build_feature_vector_includes_technical_features(ticker):
    make_price_history(ticker, count=40)
    make_scored_posts(ticker)
    vector = build_feature_vector("AAPL")
    assert "close" in vector
    assert "volume" in vector
    assert "rsi_14" in vector
    assert "sma_20" in vector


@pytest.mark.django_db
def test_build_feature_vector_includes_sentiment_features(ticker):
    make_price_history(ticker)
    make_scored_posts(ticker)
    vector = build_feature_vector("AAPL")
    assert "sentiment_mean" in vector
    assert "sentiment_std" in vector
    assert "positive_ratio" in vector


@pytest.mark.django_db
def test_build_feature_vector_handles_no_prices(ticker):
    make_scored_posts(ticker)
    vector = build_feature_vector("AAPL")
    assert vector is not None
    # Technical features should be None when no price data
    assert vector.get("rsi_14") is None


@pytest.mark.django_db
def test_build_feature_vector_handles_no_posts(ticker):
    make_price_history(ticker)
    vector = build_feature_vector("AAPL")
    assert vector is not None
    assert vector.get("sentiment_mean") is None


@pytest.mark.django_db
def test_build_feature_vector_unknown_ticker():
    vector = build_feature_vector("UNKNOWN")
    assert vector is None
