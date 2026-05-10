import pytest
from collections import Counter
from datetime import timedelta
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
def test_social_feed_orders_by_posted_at_desc_then_fetched_at(auth_client, ticker):
    newer_posted_older_fetch = SocialPost.objects.create(
        ticker=ticker,
        source="reddit",
        external_id="order_newer_posted",
        title="Newer posted",
        content="newer posted",
        cleaned_text="newer posted",
        posted_at=timezone.now(),
    )
    older_posted_newer_fetch = SocialPost.objects.create(
        ticker=ticker,
        source="stocktwits",
        external_id="order_older_posted",
        title="Older posted",
        content="older posted",
        cleaned_text="older posted",
        posted_at=timezone.now() - timedelta(days=1),
    )
    old_time = timezone.now() - timedelta(minutes=10)
    new_time = timezone.now()
    SocialPost.objects.filter(id=newer_posted_older_fetch.id).update(fetched_at=old_time)
    SocialPost.objects.filter(id=older_posted_newer_fetch.id).update(fetched_at=new_time)

    resp = auth_client.get("/api/social/feed/")
    assert resp.status_code == 200
    data = resp.json()
    ids = [row["id"] for row in data]
    assert ids.index(newer_posted_older_fetch.id) < ids.index(older_posted_newer_fetch.id)


@pytest.mark.django_db
def test_social_feed_mixed_tickers_uses_posted_at_over_latest_batch_fetch(auth_client, ticker):
    from apps.tickers.models import Ticker

    other = Ticker.objects.create(symbol="XOM", name="Exxon Mobil")
    recent_posted_old_fetch = SocialPost.objects.create(
        ticker=ticker,
        source="news_google",
        external_id="mix_recent_posted",
        title="AAPL recent posted",
        content="AAPL recent posted",
        cleaned_text="AAPL recent posted",
        posted_at=timezone.now(),
    )
    stale_posted_new_fetch = SocialPost.objects.create(
        ticker=other,
        source="news_yahoo",
        external_id="mix_stale_posted",
        title="stale posted",
        content="stale posted",
        cleaned_text="stale posted",
        posted_at=timezone.now() - timedelta(days=2),
    )
    SocialPost.objects.filter(id=recent_posted_old_fetch.id).update(
        fetched_at=timezone.now() - timedelta(hours=2)
    )
    SocialPost.objects.filter(id=stale_posted_new_fetch.id).update(fetched_at=timezone.now())

    resp = auth_client.get("/api/social/feed/")
    assert resp.status_code == 200
    ids = [row["id"] for row in resp.json()]
    assert ids.index(recent_posted_old_fetch.id) < ids.index(stale_posted_new_fetch.id)


@pytest.mark.django_db
def test_social_feed_includes_display_content_from_cleaned_text(auth_client, ticker):
    post = SocialPost.objects.create(
        ticker=ticker,
        source="reddit",
        external_id="cleaned_1",
        title="x",
        content="<div>raw html</div>",
        cleaned_text="raw html",
        posted_at=timezone.now(),
    )
    resp = auth_client.get("/api/social/feed/")
    assert resp.status_code == 200
    row = next(item for item in resp.json() if item["id"] == post.id)
    assert row["display_content"] == "raw html"
    assert row["content"] == "raw html"
    assert row["ticker"] == ticker.id
    assert row["ticker_symbol"] == ticker.symbol


@pytest.mark.django_db
def test_social_feed_symbol_filter(auth_client, ticker):
    from apps.tickers.models import Ticker
    other = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    make_post(ticker, source="reddit")
    make_post(other, source="reddit")
    resp = auth_client.get(f"/api/social/feed/?symbol={ticker.symbol}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert {row["ticker_symbol"] for row in data} == {ticker.symbol}


@pytest.mark.django_db
def test_social_feed_source_filter_applies_before_limit(auth_client, ticker):
    from apps.tickers.models import Ticker

    other = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    now = timezone.now()
    for i in range(120):
        SocialPost.objects.create(
            ticker=ticker,
            source="reddit",
            external_id=f"reddit_recent_{i}",
            title="Recent reddit",
            content="recent reddit",
            posted_at=now + timedelta(seconds=i),
        )
    google = SocialPost.objects.create(
        ticker=other,
        source="news_google",
        external_id="google_reachable",
        title="Microsoft shares move higher",
        content="MSFT earnings expectations improved.",
        posted_at=now - timedelta(days=1),
    )

    resp = auth_client.get("/api/social/feed/?source=news_google")

    assert resp.status_code == 200
    data = resp.json()
    assert [row["id"] for row in data] == [google.id]
    assert data[0]["ticker_symbol"] == "MSFT"


@pytest.mark.django_db
def test_social_feed_filters_irrelevant_ambiguous_google_news(auth_client):
    from apps.tickers.models import Ticker

    visa = Ticker.objects.create(symbol="V", name="Visa Inc.")
    SocialPost.objects.create(
        ticker=visa,
        source="news_google",
        external_id="bad_google_v",
        title="Real Madrid v FC Barcelona live stream",
        content="Watch the match online.",
        cleaned_text="Watch the match online.",
        posted_at=timezone.now(),
    )
    good = SocialPost.objects.create(
        ticker=visa,
        source="news_google",
        external_id="good_google_v",
        title="Visa shares rise after earnings",
        content="Visa revenue increased.",
        cleaned_text="Visa revenue increased.",
        posted_at=timezone.now() - timedelta(seconds=1),
    )

    resp = auth_client.get("/api/social/feed/?source=news_google")

    assert resp.status_code == 200
    data = resp.json()
    assert [row["id"] for row in data] == [good.id]


@pytest.mark.django_db
def test_global_social_feed_diversifies_unfiltered_first_page(auth_client, ticker):
    from apps.tickers.models import Ticker

    other = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    now = timezone.now()
    for i in range(80):
        SocialPost.objects.create(
            ticker=ticker,
            source="reddit",
            external_id=f"dominant_reddit_{i}",
            title="Dominant reddit",
            content="dominant reddit",
            posted_at=now + timedelta(seconds=i),
        )
    for i in range(5):
        SocialPost.objects.create(
            ticker=other,
            source="news_google",
            external_id=f"minority_google_{i}",
            title="Microsoft shares move higher",
            content="MSFT earnings expectations improved.",
            posted_at=now - timedelta(seconds=i),
        )

    resp = auth_client.get("/api/social/feed/")

    assert resp.status_code == 200
    data = resp.json()
    sources = Counter(row["source"] for row in data)
    tickers = Counter(row["ticker_symbol"] for row in data)
    assert sources["news_google"] == 5
    assert sources["reddit"] <= 40
    assert tickers[ticker.symbol] <= 15


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
