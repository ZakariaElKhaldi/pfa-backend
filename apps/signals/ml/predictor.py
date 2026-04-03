"""
ML signal predictor with rule-based fallback.
Based on Papers 1 & 4: XGBoost prediction with graceful degradation.
"""

import logging
import os

import numpy as np

from apps.signals.ml.trainer import LABEL_MAP, SignalModelTrainer

logger = logging.getLogger(__name__)


class SignalPredictor:
    """Predict trading signals using trained ML model with rule-based fallback."""

    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
        self._trainer = SignalModelTrainer()
        self._model_cache = {}

    def _load_model(self, ticker_symbol: str):
        """Load model for ticker, with caching."""
        if ticker_symbol in self._model_cache:
            return self._model_cache[ticker_symbol]

        path = os.path.join(self.model_dir, f"{ticker_symbol}.joblib")
        if not os.path.exists(path):
            return None

        try:
            model = self._trainer.load_model(path)
            self._model_cache[ticker_symbol] = model
            return model
        except Exception as e:
            logger.error("Failed to load model for %s: %s", ticker_symbol, e)
            return None

    def predict(
        self,
        ticker_symbol: str,
        feature_vector: dict | None,
        fallback_signal: str = "HOLD",
        fallback_sentiment: float = 0.0,
    ) -> dict:
        """
        Predict signal using ML model. Falls back to rule-based if:
        - No trained model exists
        - Feature vector is None/empty
        - Prediction fails
        """
        if feature_vector is None:
            return self._fallback(fallback_signal, fallback_sentiment)

        model = self._load_model(ticker_symbol)
        if model is None:
            return self._fallback(fallback_signal, fallback_sentiment)

        try:
            X = np.array([list(feature_vector.values())])
            prediction = model.predict(X)[0]
            probas = model.predict_proba(X)[0]
            confidence = float(max(probas))
            signal = LABEL_MAP.get(int(prediction), "HOLD")

            return {
                "signal": signal,
                "confidence": confidence,
                "method": "ml",
                "probabilities": {
                    LABEL_MAP[i]: float(p) for i, p in enumerate(probas)
                },
            }
        except Exception as e:
            logger.error("ML prediction failed for %s: %s", ticker_symbol, e)
            return self._fallback(fallback_signal, fallback_sentiment)

    def _fallback(self, signal: str, sentiment: float) -> dict:
        """Rule-based fallback result."""
        return {
            "signal": signal,
            "confidence": None,
            "method": "rule_based",
            "probabilities": None,
        }
