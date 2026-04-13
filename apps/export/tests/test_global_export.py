import pytest
from decimal import Decimal
from django.utils import timezone
from apps.signals.models import SignalSnapshot
from apps.tickers.models import Watchlist
from apps.portfolio.models import Trade


@pytest.mark.django_db
def test_signals_export_json(auth_client, user, ticker, seeded_portfolio):
    Watchlist.objects.create(user=user, ticker=ticker)
    SignalSnapshot.objects.create(
        ticker=ticker, signal="BUY", sentiment=0.6, momentum=0.4,
        consistency=0.8, post_count=10, bullish_ratio=0.6,
        normalized_index=0.5, time_decay_score=0.7,
        source_weighted_score=0.6, prediction_method="rule_based",
        prediction_confidence=0.75, feature_importances={},
    )
    resp = auth_client.get("/api/export/signals/?format=json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_signals_export_csv(auth_client, user, ticker, seeded_portfolio):
    Watchlist.objects.create(user=user, ticker=ticker)
    resp = auth_client.get("/api/export/signals/?format=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.get("Content-Type", "")


@pytest.mark.django_db
def test_portfolio_export_json(auth_client, user, ticker, seeded_portfolio):
    Trade.objects.create(
        portfolio=seeded_portfolio, ticker=ticker,
        side="buy", quantity=5, price=Decimal("100.00"),
        executed_at=timezone.now()
    )
    resp = auth_client.get("/api/export/portfolio/?format=json")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_portfolio_export_csv(auth_client, user, ticker, seeded_portfolio):
    resp = auth_client.get("/api/export/portfolio/?format=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.get("Content-Type", "")
