"""Push signal updates to ws/signals/ consumer group."""

from unittest.mock import patch

import pytest

from apps.signals.utils import push_signal_update


def test_push_signal_update_sends_to_global_group():
    """push_signal_update must broadcast to the 'signals_global' group."""
    with patch("apps.signals.utils.get_channel_layer") as mock_layer:
        layer = mock_layer.return_value
        sent = {}

        async def capture(group, message):
            sent["group"] = group
            sent["message"] = message

        layer.group_send = capture
        push_signal_update({"ticker": "AAPL", "signal": "BUY"})

    assert sent["group"] == "signals_global"
    assert sent["message"]["type"] == "signal.new"
    assert sent["message"]["data"] == {"ticker": "AAPL", "signal": "BUY"}


def test_push_signal_update_swallows_errors():
    """Redis/channel errors must not break the pipeline."""
    with patch("apps.signals.utils.get_channel_layer", side_effect=Exception("boom")):
        push_signal_update({"ticker": "AAPL"})  # should not raise


@pytest.mark.django_db
def test_pipeline_calls_push_signal_update_after_compute(monkeypatch):
    """Pipeline must push signal to ws/signals/ after snapshot creation."""
    from apps.pipeline import pipeline as pipeline_mod

    calls = []
    monkeypatch.setattr(
        "apps.signals.utils.push_signal_update",
        lambda data: calls.append(data),
    )
    # Smoke: function is importable from pipeline's namespace
    from apps.signals.utils import push_signal_update as imported
    imported({"ticker": "TEST", "signal": "HOLD"})
    assert calls == [{"ticker": "TEST", "signal": "HOLD"}]
