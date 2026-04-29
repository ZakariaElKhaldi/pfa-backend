"""
ML model training for signal prediction.
Based on Paper 1 (XGBoost + FinBERT features) and Paper 4 (rolling window, SMOTE).
"""

import logging

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

MIN_TRAINING_SAMPLES = 30
LABEL_MAP = {0: "HOLD", 1: "BUY", 2: "SELL"}
REVERSE_LABEL_MAP = {"HOLD": 0, "BUY": 1, "SELL": 2}

# Canonical feature order — must match training command feature list
FEATURE_NAMES = [
    "sentiment", "momentum", "consistency", "post_count",
    "bullish_ratio", "normalized_index", "time_decay_score", "source_weighted_score",
]


class SignalModelTrainer:
    """Train and evaluate XGBoost signal prediction models."""

    def train_xgboost(self, X: np.ndarray, y: np.ndarray) -> XGBClassifier:
        """
        Train an XGBoost classifier for 3-class signal prediction.
        Uses class weights to handle imbalanced data (Paper 4).
        """
        if len(X) < MIN_TRAINING_SAMPLES:
            raise ValueError(
                f"Insufficient training data: {len(X)} samples, "
                f"need at least {MIN_TRAINING_SAMPLES}"
            )

        # Compute class weights for imbalanced data handling
        classes, counts = np.unique(y, return_counts=True)
        total = len(y)
        weight_map = {c: total / (len(classes) * cnt) for c, cnt in zip(classes, counts)}
        sample_weights = np.array([weight_map[label] for label in y])

        model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
            random_state=42,
            verbosity=0,
        )
        model.fit(X, y, sample_weight=sample_weights)
        return model

    def evaluate(self, model: XGBClassifier, X: np.ndarray, y: np.ndarray) -> dict:
        """Evaluate model and return accuracy and macro F1."""
        predictions = model.predict(X)
        return {
            "accuracy": accuracy_score(y, predictions),
            "f1_macro": f1_score(y, predictions, average="macro", zero_division=0),
        }

    def save_model(self, model: XGBClassifier, path: str) -> None:
        """Save trained model to disk."""
        joblib.dump(model, path)
        logger.info("Model saved to %s", path)

    def load_model(self, path: str) -> XGBClassifier:
        """Load trained model from disk."""
        model = joblib.load(path)
        logger.info("Model loaded from %s", path)
        return model
