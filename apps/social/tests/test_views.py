import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.social.models import SocialPost
from apps.tickers.models import Ticker


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="socialtest", email="socialtest@example.com", password="pass123"
    )


@pytest.fixture
def client(user):
    c = APIClient()
    token = RefreshToken.for_user(user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return c


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL")


@pytest.mark.django_db
def test_list_posts_for_ticker(client, ticker):
    SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_REDDIT,
        external_id="abc123",
        content="AAPL is going to the moon!",
        cleaned_text="AAPL is going to the moon",
        sentiment_score=0.8,
        sentiment_label=SocialPost.LABEL_BULLISH,
        posted_at=timezone.now(),
    )
    response = client.get("/api/tickers/AAPL/posts/")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.django_db
def test_list_posts_for_ticker_orders_by_fetched_at(client, ticker):
    older = SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_REDDIT,
        external_id="ticker_old",
        content="older fetched",
        cleaned_text="older fetched",
        posted_at=timezone.now(),
    )
    newer = SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_STOCKTWITS,
        external_id="ticker_new",
        content="newer fetched",
        cleaned_text="newer fetched",
        posted_at=timezone.now() - timedelta(days=1),
    )
    SocialPost.objects.filter(id=older.id).update(fetched_at=timezone.now() - timedelta(minutes=10))
    SocialPost.objects.filter(id=newer.id).update(fetched_at=timezone.now())

    response = client.get("/api/tickers/AAPL/posts/")
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()]
    assert ids.index(newer.id) < ids.index(older.id)


@pytest.mark.django_db
def test_posts_deduplicated_within_same_ticker_source_external_id(ticker):
    SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_REDDIT,
        external_id="dup001",
        content="First",
        posted_at=timezone.now(),
    )
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        SocialPost.objects.create(
            ticker=ticker,
            source=SocialPost.SOURCE_REDDIT,
            external_id="dup001",
            content="Duplicate",
            posted_at=timezone.now(),
        )


@pytest.mark.django_db
def test_posts_allow_same_source_external_id_across_different_tickers(ticker):
    other = Ticker.objects.create(symbol="MSFT")
    SocialPost.objects.create(
        ticker=ticker,
        source=SocialPost.SOURCE_NEWS_YAHOO,
        external_id="shared-news-1",
        content="First ticker copy",
        posted_at=timezone.now(),
    )
    SocialPost.objects.create(
        ticker=other,
        source=SocialPost.SOURCE_NEWS_YAHOO,
        external_id="shared-news-1",
        content="Second ticker copy",
        posted_at=timezone.now(),
    )
    assert SocialPost.objects.filter(source=SocialPost.SOURCE_NEWS_YAHOO, external_id="shared-news-1").count() == 2
