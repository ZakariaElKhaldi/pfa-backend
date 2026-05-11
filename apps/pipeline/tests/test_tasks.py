from unittest.mock import patch

import pytest
from django.core.cache import cache

from apps.pipeline.tasks import PIPELINE_LOCK_KEY, run_pipeline
from apps.tickers.models import Ticker


@pytest.fixture(autouse=True)
def clear_pipeline_lock():
    cache.delete(PIPELINE_LOCK_KEY)
    yield
    cache.delete(PIPELINE_LOCK_KEY)


@pytest.mark.django_db
@patch("apps.pipeline.pipeline.run_pipeline_for_ticker")
def test_run_pipeline_skips_when_lock_exists(mock_run_for_ticker):
    Ticker.objects.create(symbol="AAPL")
    cache.add(PIPELINE_LOCK_KEY, "1", timeout=600)

    run_pipeline()

    mock_run_for_ticker.assert_not_called()


@pytest.mark.django_db
@patch("apps.pipeline.pipeline.run_pipeline_for_ticker")
def test_run_pipeline_releases_lock_after_processing(mock_run_for_ticker):
    Ticker.objects.create(symbol="AAPL")

    run_pipeline()

    mock_run_for_ticker.assert_called_once_with("AAPL")
    assert cache.get(PIPELINE_LOCK_KEY) is None
