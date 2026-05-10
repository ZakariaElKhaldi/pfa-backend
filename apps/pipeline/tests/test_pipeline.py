from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.pipeline.pipeline import run_pipeline_for_ticker
from apps.social.models import SocialPost
from apps.tickers.models import Ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="MSFT")


@pytest.mark.django_db
@patch("apps.market.utils.push_market_update")
@patch("apps.pipeline.pipeline.SentimentScorer")
@patch("apps.pipeline.pipeline.GoogleNewsFetcher")
@patch("apps.pipeline.pipeline.YahooNewsFetcher")
@patch("apps.pipeline.pipeline.AlpacaNewsFetcher")
@patch("apps.pipeline.pipeline.RedditFetcher")
def test_pipeline_stores_new_posts(MockReddit, MockAlpaca, MockYahoo, MockGoogle, MockScorer, mock_push, ticker):
    now = timezone.now()

    MockReddit.return_value.fetch.return_value = [
        {
            "source": "reddit",
            "external_id": "r001",
            "content": "MSFT is a solid buy right now because cloud growth is strong",
            "posted_at": now,
        }
    ]
    MockAlpaca.return_value.fetch.return_value = []
    MockYahoo.return_value.fetch.return_value = []
    MockGoogle.return_value.fetch.return_value = []
    MockScorer.return_value.score_batch.return_value = [
        {"positive_prob": 0.8, "negative_prob": 0.1, "neutral_prob": 0.1, "composite_score": 0.7, "label": "bullish"}
    ]

    run_pipeline_for_ticker("MSFT")

    assert SocialPost.objects.filter(ticker=ticker).count() == 1
    post = SocialPost.objects.get(ticker=ticker)
    assert post.sentiment_score == pytest.approx(0.7)
    assert post.sentiment_label == "bullish"


@pytest.mark.django_db
@patch("apps.market.utils.push_market_update")
@patch("apps.pipeline.pipeline.SentimentScorer")
@patch("apps.pipeline.pipeline.GoogleNewsFetcher")
@patch("apps.pipeline.pipeline.YahooNewsFetcher")
@patch("apps.pipeline.pipeline.AlpacaNewsFetcher")
@patch("apps.pipeline.pipeline.RedditFetcher")
def test_pipeline_deduplicates_posts(MockReddit, MockAlpaca, MockYahoo, MockGoogle, MockScorer, mock_push, ticker):
    now = timezone.now()
    post_data = {
        "source": "reddit",
        "external_id": "r_dup",
        "content": "MSFT cloud growth is very strong and persistent",
        "posted_at": now,
    }
    MockReddit.return_value.fetch.return_value = [post_data]
    MockAlpaca.return_value.fetch.return_value = []
    MockYahoo.return_value.fetch.return_value = []
    MockGoogle.return_value.fetch.return_value = []
    MockScorer.return_value.score_batch.return_value = [
        {"positive_prob": 0.6, "negative_prob": 0.1, "neutral_prob": 0.3, "composite_score": 0.5, "label": "bullish"}
    ]

    run_pipeline_for_ticker("MSFT")
    run_pipeline_for_ticker("MSFT")

    assert SocialPost.objects.filter(ticker=ticker).count() == 1


@pytest.mark.django_db
@patch("apps.market.utils.push_market_update")
@patch("apps.pipeline.pipeline.SentimentScorer")
@patch("apps.pipeline.pipeline.GoogleNewsFetcher")
@patch("apps.pipeline.pipeline.YahooNewsFetcher")
@patch("apps.pipeline.pipeline.AlpacaNewsFetcher")
@patch("apps.pipeline.pipeline.RedditFetcher")
def test_pipeline_continues_when_fetcher_fails(MockReddit, MockAlpaca, MockYahoo, MockGoogle, MockScorer, mock_push, ticker):
    MockReddit.return_value.fetch.side_effect = Exception("Reddit down")
    MockAlpaca.return_value.fetch.return_value = []
    MockYahoo.return_value.fetch.return_value = []
    MockGoogle.return_value.fetch.return_value = []
    MockScorer.return_value.score_batch.return_value = []

    # Should not raise
    run_pipeline_for_ticker("MSFT")


# --- Phase 1.3: Batch scoring and probability storage tests ---


@pytest.mark.django_db
@patch("apps.market.utils.push_market_update")
@patch("apps.pipeline.pipeline.SentimentScorer")
@patch("apps.pipeline.pipeline.GoogleNewsFetcher")
@patch("apps.pipeline.pipeline.YahooNewsFetcher")
@patch("apps.pipeline.pipeline.AlpacaNewsFetcher")
@patch("apps.pipeline.pipeline.RedditFetcher")
def test_pipeline_stores_individual_probabilities(MockReddit, MockAlpaca, MockYahoo, MockGoogle, MockScorer, mock_push, ticker):
    now = timezone.now()

    MockReddit.return_value.fetch.return_value = [
        {
            "source": "reddit",
            "external_id": "r_prob_1",
            "content": "MSFT cloud revenue is exploding this quarter great results",
            "posted_at": now,
        }
    ]
    MockAlpaca.return_value.fetch.return_value = []
    MockYahoo.return_value.fetch.return_value = []
    MockGoogle.return_value.fetch.return_value = []
    MockScorer.return_value.score_batch.return_value = [
        {
            "positive_prob": 0.8,
            "negative_prob": 0.1,
            "neutral_prob": 0.1,
            "composite_score": 0.7,
            "label": "bullish",
        }
    ]

    run_pipeline_for_ticker("MSFT")

    post = SocialPost.objects.get(ticker=ticker)
    assert post.positive_prob == pytest.approx(0.8)
    assert post.negative_prob == pytest.approx(0.1)
    assert post.neutral_prob == pytest.approx(0.1)
    assert post.sentiment_score == pytest.approx(0.7)
    assert post.sentiment_label == "bullish"


@pytest.mark.django_db
@patch("apps.market.utils.push_market_update")
@patch("apps.pipeline.pipeline.SentimentScorer")
@patch("apps.pipeline.pipeline.GoogleNewsFetcher")
@patch("apps.pipeline.pipeline.YahooNewsFetcher")
@patch("apps.pipeline.pipeline.AlpacaNewsFetcher")
@patch("apps.pipeline.pipeline.RedditFetcher")
def test_pipeline_uses_batch_scoring(MockReddit, MockAlpaca, MockYahoo, MockGoogle, MockScorer, mock_push, ticker):
    now = timezone.now()

    MockReddit.return_value.fetch.return_value = [
        {
            "source": "reddit",
            "external_id": f"r_batch_{i}",
            "content": f"MSFT is a great investment number {i} with solid fundamentals",
            "posted_at": now,
        }
        for i in range(3)
    ]
    MockAlpaca.return_value.fetch.return_value = []
    MockYahoo.return_value.fetch.return_value = []
    MockGoogle.return_value.fetch.return_value = []
    MockScorer.return_value.score_batch.return_value = [
        {"positive_prob": 0.7, "negative_prob": 0.1, "neutral_prob": 0.2, "composite_score": 0.6, "label": "bullish"},
        {"positive_prob": 0.3, "negative_prob": 0.5, "neutral_prob": 0.2, "composite_score": -0.2, "label": "bearish"},
        {"positive_prob": 0.4, "negative_prob": 0.3, "neutral_prob": 0.3, "composite_score": 0.1, "label": "neutral"},
    ]

    run_pipeline_for_ticker("MSFT")

    # score_batch should be called once with all texts, not score() called 3 times
    MockScorer.return_value.score_batch.assert_called_once()
    assert MockScorer.return_value.score.call_count == 0
    assert SocialPost.objects.filter(ticker=ticker, sentiment_score__isnull=False).count() == 3
