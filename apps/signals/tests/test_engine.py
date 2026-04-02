import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from apps.tickers.models import Ticker
from apps.social.models import SocialPost
from apps.market.models import PriceSnapshot
from apps.signals.engine import compute_signal
from apps.signals.models import SignalSnapshot


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL")


def make_posts(ticker, count, score):
    now = timezone.now()
    for i in range(count):
        SocialPost.objects.create(
            ticker=ticker,
            source=SocialPost.SOURCE_REDDIT,
            external_id=f"test_{i}",
            content="test",
            cleaned_text="test",
            sentiment_score=score,
            sentiment_label=SocialPost.LABEL_BULLISH if score > 0 else SocialPost.LABEL_BEARISH,
            posted_at=now - timedelta(minutes=i),
            fetched_at=now - timedelta(minutes=i),
        )


def make_prices(ticker, start_price, end_price):
    now = timezone.now()
    PriceSnapshot.objects.create(ticker=ticker, price=Decimal(str(start_price)), volume=0, timestamp=now - timedelta(minutes=25))
    PriceSnapshot.objects.create(ticker=ticker, price=Decimal(str(end_price)), volume=0, timestamp=now)


@pytest.mark.django_db
def test_buy_signal_when_sentiment_high_and_consistent(ticker):
    make_posts(ticker, count=10, score=0.7)
    make_prices(ticker, start_price=100, end_price=107)  # 7% gain → momentum ≈ 0.7
    result = compute_signal("AAPL")
    assert result is not None
    assert result["signal"] == SignalSnapshot.SIGNAL_BUY
    assert result["sentiment"] > 0.5
    assert result["consistency"] > 0.5


@pytest.mark.django_db
def test_sell_signal_when_sentiment_low_and_consistent(ticker):
    make_posts(ticker, count=10, score=-0.6)
    make_prices(ticker, start_price=100, end_price=94)  # -6% → momentum ≈ -0.6
    result = compute_signal("AAPL")
    assert result is not None
    assert result["signal"] == SignalSnapshot.SIGNAL_SELL


@pytest.mark.django_db
def test_hold_signal_when_inconsistent(ticker):
    make_posts(ticker, count=10, score=0.7)
    make_prices(ticker, start_price=100, end_price=93)  # price going down while sentiment up
    result = compute_signal("AAPL")
    assert result is not None
    assert result["signal"] == SignalSnapshot.SIGNAL_HOLD


@pytest.mark.django_db
def test_returns_none_when_no_posts(ticker):
    make_prices(ticker, start_price=100, end_price=105)
    result = compute_signal("AAPL")
    assert result is None


@pytest.mark.django_db
def test_returns_none_for_unknown_ticker():
    result = compute_signal("UNKNOWN")
    assert result is None


@pytest.mark.django_db
def test_post_count_in_result(ticker):
    make_posts(ticker, count=7, score=0.3)
    make_prices(ticker, start_price=100, end_price=100)
    result = compute_signal("AAPL")
    assert result["post_count"] == 7
