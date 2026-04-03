import numpy as np
import pytest

from apps.signals.ml.explainer import SignalExplainer
from apps.signals.ml.trainer import SignalModelTrainer


@pytest.fixture
def model_and_data():
    rng = np.random.RandomState(42)
    X = rng.randn(200, 8)
    y = np.where(X[:, 0] > 0.5, 1, np.where(X[:, 0] < -0.5, 2, 0))
    feature_names = [
        "sentiment", "momentum", "consistency", "post_count",
        "bullish_ratio", "normalized_index", "time_decay", "source_weighted",
    ]
    trainer = SignalModelTrainer()
    model = trainer.train_xgboost(X, y)
    return model, X, feature_names


def test_explain_prediction_returns_shap_values(model_and_data):
    model, X, feature_names = model_and_data
    explainer = SignalExplainer()
    result = explainer.explain_prediction(model, X[:1], feature_names)
    assert "feature_importances" in result
    assert len(result["feature_importances"]) == len(feature_names)


def test_explain_prediction_feature_names_match(model_and_data):
    model, X, feature_names = model_and_data
    explainer = SignalExplainer()
    result = explainer.explain_prediction(model, X[:1], feature_names)
    for name in feature_names:
        assert name in result["feature_importances"]


def test_explain_returns_top_features_sorted(model_and_data):
    model, X, feature_names = model_and_data
    explainer = SignalExplainer()
    result = explainer.explain_prediction(model, X[:1], feature_names, top_n=3)
    assert "top_features" in result
    assert len(result["top_features"]) == 3
    # Should be sorted by absolute SHAP value descending
    abs_values = [abs(v) for _, v in result["top_features"]]
    assert abs_values == sorted(abs_values, reverse=True)


def test_global_feature_importance(model_and_data):
    model, X, feature_names = model_and_data
    explainer = SignalExplainer()
    result = explainer.global_feature_importance(model, X[:50], feature_names)
    assert len(result) == len(feature_names)
    # All values should be non-negative (mean absolute SHAP)
    for v in result.values():
        assert v >= 0
