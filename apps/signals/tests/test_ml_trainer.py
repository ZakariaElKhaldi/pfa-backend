import os
import tempfile

import numpy as np
import pytest

from apps.signals.ml.trainer import SignalModelTrainer


def make_synthetic_data(n_samples=200, n_features=14):
    """Create synthetic training data for signal model."""
    rng = np.random.RandomState(42)
    X = rng.randn(n_samples, n_features)
    # Labels: 0=HOLD, 1=BUY, 2=SELL based on first feature
    y = np.where(X[:, 0] > 0.5, 1, np.where(X[:, 0] < -0.5, 2, 0))
    feature_names = [f"feature_{i}" for i in range(n_features)]
    return X, y, feature_names


def test_train_xgboost_returns_fitted_model():
    X, y, feature_names = make_synthetic_data()
    trainer = SignalModelTrainer()
    model = trainer.train_xgboost(X, y)
    assert model is not None
    # Model should be able to predict
    predictions = model.predict(X[:5])
    assert len(predictions) == 5
    assert all(p in [0, 1, 2] for p in predictions)


def test_train_xgboost_handles_imbalanced_data():
    """SMOTE or class weights should handle imbalanced classes."""
    rng = np.random.RandomState(42)
    X = rng.randn(100, 10)
    # Highly imbalanced: 80 HOLD, 15 BUY, 5 SELL
    y = np.array([0] * 80 + [1] * 15 + [2] * 5)
    trainer = SignalModelTrainer()
    model = trainer.train_xgboost(X, y)
    assert model is not None


def test_evaluate_model_returns_metrics():
    X, y, feature_names = make_synthetic_data(300)
    trainer = SignalModelTrainer()
    model = trainer.train_xgboost(X[:200], y[:200])
    metrics = trainer.evaluate(model, X[200:], y[200:])
    assert "accuracy" in metrics
    assert "f1_macro" in metrics
    assert 0 <= metrics["accuracy"] <= 1
    assert 0 <= metrics["f1_macro"] <= 1


def test_save_and_load_model_round_trips():
    X, y, _ = make_synthetic_data()
    trainer = SignalModelTrainer()
    model = trainer.train_xgboost(X, y)
    predictions_before = model.predict(X[:10])

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "test_model.joblib")
        trainer.save_model(model, path)
        assert os.path.exists(path)

        loaded_model = trainer.load_model(path)
        predictions_after = loaded_model.predict(X[:10])
        np.testing.assert_array_equal(predictions_before, predictions_after)


def test_train_with_insufficient_data():
    X = np.array([[1.0, 2.0]])
    y = np.array([0])
    trainer = SignalModelTrainer()
    with pytest.raises(ValueError):
        trainer.train_xgboost(X, y)


def test_predict_proba_returns_confidence():
    X, y, _ = make_synthetic_data()
    trainer = SignalModelTrainer()
    model = trainer.train_xgboost(X, y)
    probas = model.predict_proba(X[:5])
    assert probas.shape == (5, 3)  # 3 classes
    # Probabilities should sum to ~1
    for row in probas:
        assert abs(sum(row) - 1.0) < 0.01
