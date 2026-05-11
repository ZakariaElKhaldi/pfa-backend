import os
import logging

import numpy as np
from django.core.management.base import BaseCommand

from apps.signals.ml.trainer import ACTUAL_DIRECTION_LABEL_MAP, SignalModelTrainer
from apps.signals.models import SignalAccuracy
from apps.tickers.models import Ticker

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Train signal prediction model for a ticker using historical data"

    def add_arguments(self, parser):
        parser.add_argument("--ticker", type=str, required=True, help="Ticker symbol")
        parser.add_argument(
            "--lookback", type=int, default=252, help="Days of history to use"
        )
        parser.add_argument(
            "--output-dir", type=str, default="models", help="Model output directory"
        )

    def handle(self, *args, **options):
        symbol = options["ticker"].upper()
        lookback = options["lookback"]
        output_dir = options["output_dir"]

        try:
            ticker = Ticker.objects.get(symbol=symbol)
        except Ticker.DoesNotExist:
            self.stderr.write(f"Ticker {symbol} not found")
            return

        # Build training data from evaluated historical outcomes, not rule outputs.
        accuracy_records = (
            SignalAccuracy.objects.filter(signal_snapshot__ticker=ticker)
            .select_related("signal_snapshot")
            .order_by("signal_snapshot__created_at")[:lookback]
        )
        if accuracy_records.count() < 50:
            self.stderr.write(
                f"Insufficient data for {symbol}: {accuracy_records.count()} evaluated signals (need 50+)"
            )
            return

        # Build feature/label pairs from each snapshot and its observed market direction.
        X_list, y_list = [], []
        for record in accuracy_records:
            current = record.signal_snapshot
            label = ACTUAL_DIRECTION_LABEL_MAP.get(record.actual_direction)
            if label is None:
                logger.warning(
                    "Skipping %s accuracy record with unknown direction: %s",
                    symbol,
                    record.actual_direction,
                )
                continue
            features = [
                current.sentiment,
                current.momentum,
                current.consistency,
                float(current.post_count),
                current.bullish_ratio or 0.0,
                current.normalized_index or 0.0,
                current.time_decay_score or 0.0,
                current.source_weighted_score or 0.0,
            ]
            X_list.append(features)
            y_list.append(label)

        if len(X_list) < 50:
            self.stderr.write(
                f"Insufficient usable data for {symbol}: {len(X_list)} evaluated signals (need 50+)"
            )
            return

        X = np.array(X_list)
        y = np.array(y_list)

        trainer = SignalModelTrainer()
        model = trainer.train_xgboost(X, y)

        # Evaluate on last 20%
        split = int(len(X) * 0.8)
        metrics = trainer.evaluate(model, X[split:], y[split:])
        self.stdout.write(
            f"Model trained: accuracy={metrics['accuracy']:.3f}, "
            f"f1_macro={metrics['f1_macro']:.3f}"
        )

        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{symbol}.joblib")
        trainer.save_model(model, path)
