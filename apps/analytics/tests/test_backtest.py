import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.market.models import PriceSnapshot
from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker

from apps.analytics.services import run_backtest
from apps.analytics.models import BacktestRun


@pytest.fixture
def deterministic_setup(db):
    user = CustomUser.objects.create_user(
        username="bt", email="bt@x.com", password="p", role="analyst",
    )
    ticker = Ticker.objects.create(symbol="AAPL", name="Apple")
    base = timezone.now() - timedelta(days=10)

    for i, sig in enumerate(["HOLD", "BUY", "BUY", "SELL", "BUY", "SELL"]):
        s = SignalSnapshot.objects.create(
            ticker=ticker, sentiment=0.0, momentum=0.0, consistency=0.5,
            signal=sig, post_count=1,
        )
        SignalSnapshot.objects.filter(pk=s.pk).update(
            created_at=base + timedelta(hours=i)
        )
    for i, price in enumerate([100, 100, 110, 121, 110, 132]):
        PriceSnapshot.objects.create(
            ticker=ticker, price=Decimal(str(price)), volume=1,
            timestamp=base + timedelta(hours=i),
        )
    return user, ticker, base


@pytest.mark.django_db
class TestRunBacktest:
    def test_signal_strategy_produces_metrics(self, deterministic_setup):
        user, ticker, base = deterministic_setup
        run = run_backtest(
            user=user,
            symbol="AAPL",
            start=base,
            end=base + timedelta(hours=6),
            strategy="signal",
            params={},
        )
        assert run.status == "ok"
        assert run.ticker == ticker
        assert run.user == user
        assert isinstance(run.trades, list)
        assert isinstance(run.equity_curve, list)
        assert run.total_return is not None
        assert 0.0 <= run.win_rate <= 1.0

    def test_unknown_symbol_raises(self, deterministic_setup):
        user, _, base = deterministic_setup
        with pytest.raises(ValueError, match="Unknown ticker"):
            run_backtest(
                user=user, symbol="ZZZZ",
                start=base, end=base + timedelta(hours=6),
                strategy="signal", params={},
            )

    def test_window_too_long_raises(self, deterministic_setup):
        user, _, base = deterministic_setup
        with pytest.raises(ValueError, match="window cannot exceed 365 days"):
            run_backtest(
                user=user, symbol="AAPL",
                start=base, end=base + timedelta(days=400),
                strategy="signal", params={},
            )

    def test_unsupported_strategy_raises(self, deterministic_setup):
        user, _, base = deterministic_setup
        with pytest.raises(ValueError, match="not yet implemented"):
            run_backtest(
                user=user, symbol="AAPL",
                start=base, end=base + timedelta(hours=6),
                strategy="sentiment_threshold", params={},
            )
