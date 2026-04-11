import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="signaltest", email="signaltest@example.com", password="pass123"
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


@pytest.fixture
def signal_snapshot(ticker):
    return SignalSnapshot.objects.create(
        ticker=ticker,
        sentiment=0.6,
        momentum=0.4,
        consistency=0.8,
        signal="BUY",
        post_count=15,
        bullish_ratio=1.2,
        normalized_index=0.5,
        time_decay_score=0.62,
        source_weighted_score=0.58,
        positive_count=10,
        negative_count=3,
        neutral_count=2,
        prediction_method="rule_based",
        prediction_confidence=None,
        feature_importances={"sentiment": 0.3, "momentum": 0.2},
    )


@pytest.mark.django_db
def test_signal_endpoint_includes_aggregation_fields(client, signal_snapshot):
    resp = client.get("/api/tickers/AAPL/signal/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["signal"] == "BUY"
    assert data["bullish_ratio"] == pytest.approx(1.2)
    assert data["normalized_index"] == pytest.approx(0.5)
    assert data["time_decay_score"] == pytest.approx(0.62)
    assert data["source_weighted_score"] == pytest.approx(0.58)
    assert data["positive_count"] == 10
    assert data["prediction_method"] == "rule_based"


@pytest.mark.django_db
def test_signal_history_endpoint(client, signal_snapshot):
    # Create a second snapshot
    SignalSnapshot.objects.create(
        ticker=signal_snapshot.ticker,
        sentiment=0.3,
        momentum=0.1,
        consistency=0.9,
        signal="HOLD",
        post_count=5,
    )
    resp = client.get("/api/tickers/AAPL/signal/history/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2


@pytest.mark.django_db
def test_signal_explain_endpoint(client, signal_snapshot):
    resp = client.get("/api/tickers/AAPL/signal/explain/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["signal"] == "BUY"
    assert data["prediction_method"] == "rule_based"
    assert data["feature_importances"] == {"sentiment": 0.3, "momentum": 0.2}
    assert data["aggregation"]["bullish_ratio"] == pytest.approx(1.2)
    assert data["counts"]["positive"] == 10
    assert data["counts"]["total"] == 15


@pytest.mark.django_db
def test_signal_explain_404_when_no_signal(client, ticker):
    resp = client.get("/api/tickers/AAPL/signal/explain/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_indicators_endpoint(client, ticker):
    from decimal import Decimal
    from apps.market.models import PriceSnapshot
    now = timezone.now()
    from datetime import timedelta
    for i in range(25):
        PriceSnapshot.objects.create(
            ticker=ticker,
            price=Decimal(str(100 + i)),
            volume=1000000,
            timestamp=now - timedelta(days=25 - i),
        )
    resp = client.get("/api/tickers/AAPL/indicators/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert data["close"] == 124.0
    assert data["sma_20"] is not None
    assert data["rsi_14"] is not None
