import pytest
from unittest.mock import patch, MagicMock, call
from django.utils import timezone
from apps.tickers.models import Ticker
from apps.social.models import SocialPost
from apps.pipeline.pipeline import run_pipeline_for_ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="MSFT")


@pytest.mark.django_db
@patch("apps.market.utils.push_market_update")
@patch("apps.pipeline.pipeline.SentimentScorer")
@patch("apps.pipeline.pipeline.StockTwitsFetcher")
@patch("apps.pipeline.pipeline.RedditFetcher")
def test_pipeline_stores_new_posts(
    MockReddit, MockST, MockScorer, mock_push, ticker
):
    now = timezone.now()

    MockReddit.return_value.fetch.return_value = [
        {
            "source": "reddit",
            "external_id": "r001",
            "content": "MSFT is a solid buy right now because cloud growth is strong",
            "posted_at": now,
        }
    ]
    MockST.return_value.fetch.return_value = []
    MockScorer.return_value.score.return_value = (0.7, "bullish")

    run_pipeline_for_ticker("MSFT")

    assert SocialPost.objects.filter(ticker=ticker).count() == 1
    post = SocialPost.objects.get(ticker=ticker)
    assert post.sentiment_score == 0.7
    assert post.sentiment_label == "bullish"


@pytest.mark.django_db
@patch("apps.market.utils.push_market_update")
@patch("apps.pipeline.pipeline.SentimentScorer")
@patch("apps.pipeline.pipeline.StockTwitsFetcher")
@patch("apps.pipeline.pipeline.RedditFetcher")
def test_pipeline_deduplicates_posts(
    MockReddit, MockST, MockScorer, mock_push, ticker
):
    now = timezone.now()
    post_data = {
        "source": "reddit",
        "external_id": "r_dup",
        "content": "MSFT cloud growth is very strong and persistent",
        "posted_at": now,
    }
    MockReddit.return_value.fetch.return_value = [post_data]
    MockST.return_value.fetch.return_value = []
    MockScorer.return_value.score.return_value = (0.5, "bullish")

    run_pipeline_for_ticker("MSFT")
    run_pipeline_for_ticker("MSFT")

    assert SocialPost.objects.filter(ticker=ticker).count() == 1


@pytest.mark.django_db
@patch("apps.market.utils.push_market_update")
@patch("apps.pipeline.pipeline.SentimentScorer")
@patch("apps.pipeline.pipeline.StockTwitsFetcher")
@patch("apps.pipeline.pipeline.RedditFetcher")
def test_pipeline_continues_when_fetcher_fails(
    MockReddit, MockST, MockScorer, mock_push, ticker
):
    MockReddit.return_value.fetch.side_effect = Exception("Reddit down")
    MockST.return_value.fetch.return_value = []
    MockScorer.return_value.score.return_value = (0.0, "neutral")

    # Should not raise
    run_pipeline_for_ticker("MSFT")
