import pytest
from decimal import Decimal

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.tickers.models import Ticker
from apps.portfolio.models import Portfolio


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123", role="user"
    )


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(
        username="adminuser", email="admin@example.com", password="adminpass123", role="admin"
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    token = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def analyst_user(db):
    return CustomUser.objects.create_user(
        username="analystuser", email="analyst@example.com",
        password="analystpass123", role="analyst",
    )


@pytest.fixture
def analyst_client(analyst_user):
    client = APIClient()
    token = RefreshToken.for_user(analyst_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL", name="Apple Inc.")


@pytest.fixture
def seeded_portfolio(user):
    return Portfolio.objects.create(user=user, cash=Decimal("100000.00"))
