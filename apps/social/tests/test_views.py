import pytest
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
    assert response.json()["count"] == 1


@pytest.mark.django_db
def test_posts_deduplicated_by_source_and_external_id(ticker):
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
