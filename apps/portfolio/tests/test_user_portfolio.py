import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.portfolio.models import Portfolio


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
class TestUserPortfolio:
    def test_get_portfolio_creates_if_missing(self, auth_client, user):
        resp = auth_client.get("/api/portfolio/")
        assert resp.status_code == 200
        assert Portfolio.objects.filter(user=user).exists()

    def test_portfolio_isolation(self, auth_client, user, db):
        other = CustomUser.objects.create_user(
            username="other", email="other@example.com", password="pass123"
        )
        Portfolio.objects.create(user=other, cash=Decimal("50000.00"))
        resp = auth_client.get("/api/portfolio/")
        assert resp.data["cash"] == "100000.00"

    def test_unauthenticated_rejected(self):
        client = APIClient()
        resp = client.get("/api/portfolio/")
        assert resp.status_code == 401
