from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync

from apps.social.models import SocialPost
from apps.social.news_stream import AlpacaNewsStreamManager
from apps.tickers.models import Ticker


@pytest.mark.django_db
@patch("apps.pipeline.pipeline.run_pipeline_for_ticker")
def test_handle_news_creates_post_and_triggers_pipeline(mock_run_pipeline):
    Ticker.objects.create(symbol="MSFT")
    manager = AlpacaNewsStreamManager()

    news = SimpleNamespace(
        id=1001,
        symbols=["MSFT"],
        headline="Microsoft launches new AI feature",
        summary="Strong momentum in enterprise adoption.",
        url="https://example.com/news/1001",
        created_at=datetime.now(tz=timezone.utc),
    )

    async_to_sync(manager.handle_news)(news)

    assert SocialPost.objects.filter(source="news_alpaca", external_id="1001").count() == 1
    mock_run_pipeline.assert_called_once_with("MSFT")


@pytest.mark.django_db
@patch("apps.pipeline.pipeline.run_pipeline_for_ticker")
def test_handle_news_skips_duplicate_external_id(mock_run_pipeline):
    ticker = Ticker.objects.create(symbol="MSFT")
    manager = AlpacaNewsStreamManager()

    SocialPost.objects.create(
        ticker=ticker,
        source="news_alpaca",
        external_id="1002",
        title="Existing news",
        url="https://example.com/news/1002",
        content="Already ingested",
        cleaned_text="already ingested",
        posted_at=datetime.now(tz=timezone.utc),
    )

    news = SimpleNamespace(
        id=1002,
        symbols=["MSFT"],
        headline="Existing news",
        summary="Already ingested",
        url="https://example.com/news/1002",
        created_at=datetime.now(tz=timezone.utc),
    )

    async_to_sync(manager.handle_news)(news)

    assert SocialPost.objects.filter(source="news_alpaca", external_id="1002").count() == 1
    mock_run_pipeline.assert_not_called()


@pytest.mark.django_db
@patch("apps.pipeline.pipeline.run_pipeline_for_ticker")
def test_handle_news_allows_same_external_id_for_different_tickers(mock_run_pipeline):
    Ticker.objects.create(symbol="MSFT")
    Ticker.objects.create(symbol="AAPL")
    manager = AlpacaNewsStreamManager()

    news = SimpleNamespace(
        id=1003,
        symbols=["MSFT", "AAPL"],
        headline="Shared market-wide update",
        summary="The same upstream article references both symbols.",
        url="https://example.com/news/1003",
        created_at=datetime.now(tz=timezone.utc),
    )

    async_to_sync(manager.handle_news)(news)

    posts = SocialPost.objects.filter(source="news_alpaca", external_id="1003")
    assert posts.count() == 2
    assert set(posts.values_list("ticker__symbol", flat=True)) == {"MSFT", "AAPL"}
    assert mock_run_pipeline.call_count == 2
