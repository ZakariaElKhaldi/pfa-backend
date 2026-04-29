import logging

from apps.signals.models import AlertFlag

logger = logging.getLogger(__name__)

CONSISTENCY_THRESHOLD = 0.35
MIN_POST_COUNT = 5
EXTREME_SENTIMENT_THRESHOLD = 0.7


def check_and_create_alert(ticker, signal_data: dict) -> AlertFlag | None:
    """
    Creates an AlertFlag if:
      - consistency < CONSISTENCY_THRESHOLD AND post_count >= MIN_POST_COUNT

    Alert type:
      - extreme_sentiment if |sentiment| > EXTREME_SENTIMENT_THRESHOLD
      - divergence otherwise
    """
    consistency = signal_data["consistency"]
    post_count = signal_data["post_count"]
    sentiment = signal_data["sentiment"]
    momentum = signal_data["momentum"]
    hype_dampened = signal_data.get("hype_dampened", False)

    if hype_dampened:
        alert_type = AlertFlag.TYPE_HYPE_FADE
    elif consistency >= CONSISTENCY_THRESHOLD or post_count < MIN_POST_COUNT:
        return None
    else:
        alert_type = (
            AlertFlag.TYPE_EXTREME
            if abs(sentiment) > EXTREME_SENTIMENT_THRESHOLD
            else AlertFlag.TYPE_DIVERGENCE
        )

    alert = AlertFlag.objects.create(
        ticker=ticker,
        type=alert_type,
        sentiment=sentiment,
        momentum=momentum,
        consistency=consistency,
    )
    logger.info("Alert created: %s for %s", alert_type, ticker.symbol)

    from apps.events.bus import publish
    from apps.events.types import ALERT_CREATED

    publish(ALERT_CREATED, {
        "ticker": ticker.symbol,
        "alert_type": alert_type,
        "sentiment": sentiment,
        "momentum": momentum,
        "consistency": consistency,
    })

    return alert
