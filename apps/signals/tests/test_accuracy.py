import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from apps.tickers.models import Ticker
from apps.signals.models import SignalSnapshot, SignalAccuracy
from apps.market.models import PriceSnapshot
from apps.signals.tasks import evaluate_signal_accuracy


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL", name="Apple Inc.")


@pytest.mark.django_db
class TestSignalAccuracy:
    def test_evaluate_correct_buy_signal(self, ticker):
        now = timezone.now()
        snapshot = SignalSnapshot.objects.create(
            ticker=ticker, sentiment=0.8, momentum=0.5, consistency=0.7,
            signal="BUY", post_count=10,
        )
        # Backdate created_at (auto_now_add bypass via update())
        SignalSnapshot.objects.filter(pk=snapshot.pk).update(
            created_at=now - timedelta(hours=2)
        )
        snapshot.refresh_from_db()
        # Price went up after signal
        PriceSnapshot.objects.create(
            ticker=ticker, price=Decimal("100.00"),
            timestamp=now - timedelta(hours=2),
        )
        PriceSnapshot.objects.create(
            ticker=ticker, price=Decimal("105.00"),
            timestamp=now - timedelta(minutes=55),
        )
        evaluate_signal_accuracy()
        acc = SignalAccuracy.objects.get(signal_snapshot=snapshot)
        assert acc.predicted == "BUY"
        assert acc.actual_direction == "UP"
        assert acc.accuracy_1h is True

    def test_skips_already_evaluated(self, ticker):
        now = timezone.now()
        snapshot = SignalSnapshot.objects.create(
            ticker=ticker, sentiment=0.8, momentum=0.5, consistency=0.7,
            signal="BUY", post_count=10,
        )
        SignalSnapshot.objects.filter(pk=snapshot.pk).update(
            created_at=now - timedelta(hours=2)
        )
        snapshot.refresh_from_db()
        PriceSnapshot.objects.create(
            ticker=ticker, price=Decimal("100.00"),
            timestamp=now - timedelta(hours=2),
        )
        PriceSnapshot.objects.create(
            ticker=ticker, price=Decimal("105.00"),
            timestamp=now - timedelta(minutes=55),
        )
        evaluate_signal_accuracy()
        evaluate_signal_accuracy()  # second run
        assert SignalAccuracy.objects.filter(signal_snapshot=snapshot).count() == 1
