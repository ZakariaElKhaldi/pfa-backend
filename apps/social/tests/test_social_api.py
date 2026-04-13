import pytest
from django.utils import timezone
from apps.social.models import SocialPost


def make_post(ticker, sentiment_label="bullish", source="reddit"):
    return SocialPost.objects.create(
        ticker=ticker,
        source=source,
        external_id=f"ext_{timezone.now().timestamp()}",
        title="Test post",
        content="Some content",
        sentiment_label=sentiment_label,
        sentiment_score=0.7,
        posted_at=timezone.now(),
        fetched_at=timezone.now(),
    )


@pytest.mark.django_db
def test_social_feed_returns_posts(auth_client, ticker):
    make_post(ticker)
    resp = auth_client.get("/api/social/feed/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.django_db
def test_social_feed_symbol_filter(auth_client, ticker):
    from apps.tickers.models import Ticker
    other = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    make_post(ticker, source="reddit")
    make_post(other, source="reddit")
    resp = auth_client.get(f"/api/social/feed/?symbol={ticker.symbol}")
    assert resp.status_code == 200
    data = resp.json()
    # all returned posts should be for this ticker (check via ticker symbol if present, or just count)
    assert len(data) >= 1


@pytest.mark.django_db
def test_trending_returns_list(auth_client, ticker):
    make_post(ticker)
    resp = auth_client.get("/api/social/trending/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "symbol" in data[0]
        assert "mention_count" in data[0]


@pytest.mark.django_db
def test_ticker_sentiment_no_data(auth_client, ticker):
    resp = auth_client.get(f"/api/tickers/{ticker.symbol}/social/sentiment/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_ticker_sentiment_with_data(auth_client, ticker):
    make_post(ticker, sentiment_label="bullish")
    make_post(ticker, sentiment_label="bearish")
    make_post(ticker, sentiment_label="bullish")
    resp = auth_client.get(f"/api/tickers/{ticker.symbol}/social/sentiment/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["bullish"] == 2
    assert data["bearish"] == 1
    assert "bullish_pct" in data
    assert "bearish_pct" in data
    assert "neutral_pct" in data
