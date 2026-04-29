import os
import logging

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.signals.ml.trainer import REVERSE_LABEL_MAP, SignalModelTrainer
from apps.signals.models import SignalSnapshot
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

        # Build training data from historical signal snapshots
        snapshots = SignalSnapshot.objects.filter(ticker=ticker).order_by("created_at")[
            :lookback
        ]
        if snapshots.count() < 50:
            self.stderr.write(
                f"Insufficient data for {symbol}: {snapshots.count()} snapshots (need 50+)"
            )
            return

        # Build feature/label pairs from consecutive snapshots
        X_list, y_list = [], []
        snapshot_list = list(snapshots)
        for i in range(len(snapshot_list) - 1):
            current = snapshot_list[i]
            next_snap = snapshot_list[i + 1]
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
            label = REVERSE_LABEL_MAP.get(next_snap.signal, 0)
            X_list.append(features)
            y_list.append(label)

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
        self.stdout.write(f"Model saved to {path}")
