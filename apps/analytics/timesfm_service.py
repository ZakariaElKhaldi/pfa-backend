"""
TimesFM Volume Forecasting Service.

Uses Google's TimesFM 1.0 (200M) foundation model to generate
zero-shot 30-day volume forecasts from historical daily volume data.

The model is lazily loaded as a process-level singleton behind a
threading lock so concurrent Django requests don't race on init.
"""

import logging
import threading

import numpy as np
try:
    import timesfm
except ModuleNotFoundError:  # pragma: no cover - optional heavy dependency in tests
    timesfm = None

logger = logging.getLogger(__name__)

_tfm_model = None
_tfm_lock = threading.Lock()


def get_timesfm_model():
    """Return the TimesFM model singleton (lazy, thread-safe)."""
    global _tfm_model
    if timesfm is None:
        raise RuntimeError("TimesFM dependency is not installed.")
    if _tfm_model is not None:
        return _tfm_model

    with _tfm_lock:
        # Double-checked locking: another thread may have initialized
        # while we were waiting for the lock.
        if _tfm_model is not None:
            return _tfm_model

        logger.info("Initializing TimesFM model from HuggingFace…")
        _tfm_model = timesfm.TimesFm(
            hparams=timesfm.TimesFmHparams(
                context_len=512,
                horizon_len=128,     # max horizon the model supports
                input_patch_len=32,
                output_patch_len=128,
                num_layers=20,
                model_dims=1280,
                use_positional_embedding=False,
            ),
            checkpoint=timesfm.TimesFmCheckpoint(
                huggingface_repo_id="google/timesfm-1.0-200m-pytorch",
            ),
        )
        logger.info("TimesFM model ready.")
        return _tfm_model


def forecast_series(
    history: list[float],
    horizon: int = 30,
    clip_zero: bool = False,
) -> list[float]:
    """
    Given daily history, return the next *horizon* days forecast.

    Args:
        history: Ordered list of daily values (oldest → newest).
        horizon: Number of future days to predict (max 128).
        clip_zero: If True, clips negative predictions to 0.0.

    Returns:
        List of predicted daily values.
    """
    if len(history) < 10:
        raise ValueError("Need at least 10 historical data points.")

    model = get_timesfm_model()

    # TimesFM expects list-of-arrays; freq=0 → high-frequency (daily).
    input_data = np.array(history, dtype=np.float32)
    point_forecast, _ = model.forecast([input_data], freq=[0])

    preds = point_forecast[0, :horizon].tolist()

    if clip_zero:
        return [max(0.0, p) for p in preds]
    return preds

def forecast_volume(
    volume_history: list[float],
    horizon: int = 30,
) -> list[float]:
    """
    Wrapper around forecast_series that enforces non-negative volume.
    """
    return forecast_series(volume_history, horizon, clip_zero=True)
