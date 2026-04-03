"""
SHAP-based explainability for signal predictions.
Based on Paper 1: TreeSHAP for XGBoost feature importance.
FinBERT sentiment features contributed 28.6% to model importance in the study.
"""

import logging

import numpy as np
import shap

logger = logging.getLogger(__name__)


class SignalExplainer:
    """Explain signal predictions using SHAP values."""

    def explain_prediction(
        self,
        model,
        X: np.ndarray,
        feature_names: list[str],
        top_n: int = 5,
    ) -> dict:
        """
        Explain a single prediction using TreeSHAP.
        Returns feature importances and top contributing features.
        """
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        # For multi-class, shap_values is a list of arrays (one per class).
        # Use the predicted class's SHAP values.
        prediction = model.predict(X)[0]
        if isinstance(shap_values, list):
            values = shap_values[int(prediction)][0]
        else:
            # Some versions return 3D array
            if shap_values.ndim == 3:
                values = shap_values[0, :, int(prediction)]
            else:
                values = shap_values[0]

        feature_importances = {
            name: float(val) for name, val in zip(feature_names, values)
        }

        # Top N features sorted by absolute SHAP value
        sorted_features = sorted(
            feature_importances.items(), key=lambda x: abs(x[1]), reverse=True
        )
        top_features = sorted_features[:top_n]

        return {
            "feature_importances": feature_importances,
            "top_features": top_features,
            "base_value": float(
                explainer.expected_value[int(prediction)]
                if isinstance(explainer.expected_value, (list, np.ndarray))
                else explainer.expected_value
            ),
        }

    def global_feature_importance(
        self,
        model,
        X_background: np.ndarray,
        feature_names: list[str],
    ) -> dict:
        """Mean |SHAP| across a background dataset."""
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_background)

        # Average absolute SHAP across all classes and samples
        if isinstance(shap_values, list):
            # list of (n_samples, n_features) arrays, one per class
            stacked = np.stack([np.abs(sv) for sv in shap_values], axis=0)
            # mean over classes then samples -> (n_features,)
            mean_abs = np.mean(stacked, axis=(0, 1))
        else:
            shap_arr = np.abs(shap_values)
            if shap_arr.ndim == 3:
                mean_abs = np.mean(shap_arr, axis=(0, 2))
            else:
                mean_abs = np.mean(shap_arr, axis=0)
        return {name: float(val) for name, val in zip(feature_names, mean_abs)}
