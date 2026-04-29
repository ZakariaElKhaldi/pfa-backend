import pytest

from apps.signals.alerts import check_and_create_alert
from apps.signals.models import AlertFlag
from apps.tickers.models import Ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL")


@pytest.mark.django_db
def test_creates_divergence_alert_when_consistency_low(ticker):
    data = {"sentiment": 0.4, "momentum": -0.4, "consistency": 0.2, "post_count": 10}
    check_and_create_alert(ticker, data)
    assert AlertFlag.objects.filter(ticker=ticker, type=AlertFlag.TYPE_DIVERGENCE).count() == 1


@pytest.mark.django_db
def test_creates_extreme_sentiment_alert_when_sentiment_very_high(ticker):
    data = {"sentiment": 0.9, "momentum": -0.5, "consistency": 0.1, "post_count": 8}
    check_and_create_alert(ticker, data)
    alert = AlertFlag.objects.get(ticker=ticker)
    assert alert.type == AlertFlag.TYPE_EXTREME


@pytest.mark.django_db
def test_no_alert_when_consistency_sufficient(ticker):
    data = {"sentiment": 0.6, "momentum": 0.5, "consistency": 0.6, "post_count": 10}
    check_and_create_alert(ticker, data)
    assert AlertFlag.objects.filter(ticker=ticker).count() == 0


@pytest.mark.django_db
def test_no_alert_when_post_count_below_threshold(ticker):
    data = {"sentiment": 0.4, "momentum": -0.5, "consistency": 0.1, "post_count": 3}
    check_and_create_alert(ticker, data)
    assert AlertFlag.objects.filter(ticker=ticker).count() == 0


@pytest.mark.django_db
def test_alert_defaults_to_unresolved(ticker):
    data = {"sentiment": 0.2, "momentum": -0.6, "consistency": 0.3, "post_count": 7}
    check_and_create_alert(ticker, data)
    alert = AlertFlag.objects.get(ticker=ticker)
    assert alert.resolved is False


# --- Fade-the-hype alert (Long 2024) ---


@pytest.mark.django_db
def test_hype_fade_alert_when_dampener_fires(ticker):
    """hype_dampened=True flag → creates TYPE_HYPE_FADE alert regardless of consistency."""
    data = {
        "sentiment": 0.35,
        "momentum": 0.7,
        "consistency": 0.8,
        "post_count": 100,
        "hype_dampened": True,
        "mention_rate_z": 3.5,
    }
    check_and_create_alert(ticker, data)
    alert = AlertFlag.objects.get(ticker=ticker)
    assert alert.type == AlertFlag.TYPE_HYPE_FADE


@pytest.mark.django_db
def test_no_hype_fade_alert_when_dampener_inactive(ticker):
    """hype_dampened=False → no hype_fade alert (other rules may still fire)."""
    data = {
        "sentiment": 0.6,
        "momentum": 0.6,
        "consistency": 0.9,
        "post_count": 10,
        "hype_dampened": False,
        "mention_rate_z": 0.5,
    }
    check_and_create_alert(ticker, data)
    assert AlertFlag.objects.filter(ticker=ticker, type=AlertFlag.TYPE_HYPE_FADE).count() == 0
