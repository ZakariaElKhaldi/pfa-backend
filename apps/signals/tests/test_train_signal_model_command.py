from decimal import Decimal
from unittest.mock import patch

import numpy as np
import pytest
from django.core.management import call_command

from apps.signals.models import SignalAccuracy, SignalSnapshot


@pytest.mark.django_db
def test_train_signal_model_uses_actual_market_direction(ticker, tmp_path):
    for i in range(50):
        snapshot = SignalSnapshot.objects.create(
            ticker=ticker,
            sentiment=0.8,
            momentum=0.4,
            consistency=0.9,
            signal="BUY",
            post_count=i + 1,
        )
        SignalAccuracy.objects.create(
            signal_snapshot=snapshot,
            predicted="BUY",
            actual_direction="DOWN",
            price_at_signal=Decimal("100.00"),
            price_after_1h=Decimal("99.00"),
            price_after_24h=None,
            accuracy_1h=False,
            accuracy_24h=None,
        )

    captured = {}

    def fake_train(self, X, y):
        captured["X"] = X
        captured["y"] = y
        return object()

    with (
        patch("apps.signals.ml.trainer.SignalModelTrainer.train_xgboost", fake_train),
        patch(
            "apps.signals.ml.trainer.SignalModelTrainer.evaluate",
            return_value={"accuracy": 0.25, "f1_macro": 0.2},
        ),
        patch("apps.signals.ml.trainer.SignalModelTrainer.save_model"),
    ):
        call_command(
            "train_signal_model",
            ticker=ticker.symbol,
            output_dir=str(tmp_path),
        )

    assert captured["X"].shape == (50, 8)
    np.testing.assert_array_equal(captured["y"], np.array([2] * 50))
