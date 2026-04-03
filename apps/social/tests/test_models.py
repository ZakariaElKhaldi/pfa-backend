import pytest
from django.utils import timezone

from apps.social.models import SocialPost
from apps.tickers.models import Ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL")


@pytest.mark.django_db
def test_social_post_has_positive_prob_field(ticker):
    post = SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_REDDIT,
        external_id="test_prob_1",
        content="test",
        posted_at=timezone.now(),
        positive_prob=0.8,
    )
    post.refresh_from_db()
    assert post.positive_prob == pytest.approx(0.8)


@pytest.mark.django_db
def test_social_post_has_negative_prob_field(ticker):
    post = SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_REDDIT,
        external_id="test_prob_2",
        content="test",
        posted_at=timezone.now(),
        negative_prob=0.15,
    )
    post.refresh_from_db()
    assert post.negative_prob == pytest.approx(0.15)


@pytest.mark.django_db
def test_social_post_has_neutral_prob_field(ticker):
    post = SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_REDDIT,
        external_id="test_prob_3",
        content="test",
        posted_at=timezone.now(),
        neutral_prob=0.5,
    )
    post.refresh_from_db()
    assert post.neutral_prob == pytest.approx(0.5)


@pytest.mark.django_db
def test_social_post_prob_fields_default_null(ticker):
    post = SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_REDDIT,
        external_id="test_prob_4",
        content="test",
        posted_at=timezone.now(),
    )
    post.refresh_from_db()
    assert post.positive_prob is None
    assert post.negative_prob is None
    assert post.neutral_prob is None


@pytest.mark.django_db
def test_social_post_backward_compatible_sentiment_score(ticker):
    post = SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_REDDIT,
        external_id="test_prob_5",
        content="test",
        posted_at=timezone.now(),
        sentiment_score=0.6,
        sentiment_label="bullish",
        positive_prob=0.8,
        negative_prob=0.1,
        neutral_prob=0.1,
    )
    post.refresh_from_db()
    assert post.sentiment_score == pytest.approx(0.6)
    assert post.sentiment_label == "bullish"
    assert post.positive_prob == pytest.approx(0.8)
