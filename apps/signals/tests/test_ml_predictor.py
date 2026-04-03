import os
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from apps.signals.ml.predictor import SignalPredictor
from apps.signals.ml.trainer import SignalModelTrainer


@pytest.fixture
def trained_model_dir():
    """Create a temp dir with a trained model."""
    rng = np.random.RandomState(42)
    X = rng.randn(200, 14)
    y = np.where(X[:, 0] > 0.5, 1, np.where(X[:, 0] < -0.5, 2, 0))
    trainer = SignalModelTrainer()
    model = trainer.train_xgboost(X, y)

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "AAPL.joblib")
        trainer.save_model(model, path)
        yield tmpdir


def test_predict_returns_signal_and_confidence(trained_model_dir):
    predictor = SignalPredictor(model_dir=trained_model_dir)
    feature_vector = {f"feature_{i}": float(i) * 0.1 for i in range(14)}

    result = predictor.predict("AAPL", feature_vector)
    assert result["signal"] in ["BUY", "SELL", "HOLD"]
    assert 0 <= result["confidence"] <= 1
    assert result["method"] == "ml"


def test_predict_falls_back_when_no_model():
    predictor = SignalPredictor(model_dir="/nonexistent/path")
    feature_vector = {f"feature_{i}": float(i) * 0.1 for i in range(14)}

    result = predictor.predict(
        "AAPL", feature_vector, fallback_signal="HOLD", fallback_sentiment=0.3
    )
    assert result["signal"] == "HOLD"
    assert result["method"] == "rule_based"


def test_predict_falls_back_when_features_none():
    predictor = SignalPredictor(model_dir="/tmp")
    result = predictor.predict("AAPL", None, fallback_signal="SELL", fallback_sentiment=-0.5)
    assert result["signal"] == "SELL"
    assert result["method"] == "rule_based"


def test_predict_returns_correct_label_mapping(trained_model_dir):
    predictor = SignalPredictor(model_dir=trained_model_dir)
    # Test multiple predictions to cover different classes
    signals_seen = set()
    for seed in range(50):
        rng = np.random.RandomState(seed)
        fv = {f"feature_{i}": rng.randn() for i in range(14)}
        result = predictor.predict("AAPL", fv)
        signals_seen.add(result["signal"])
        assert result["signal"] in ["BUY", "SELL", "HOLD"]

    # Should see at least 2 different signals across 50 predictions
    assert len(signals_seen) >= 2
