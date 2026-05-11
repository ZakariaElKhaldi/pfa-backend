import logging
from datetime import timedelta

from django.utils import timezone

from apps.signals.models import AlertFlag

logger = logging.getLogger(__name__)

CONSISTENCY_THRESHOLD = 0.35
MIN_POST_COUNT = 5
EXTREME_SENTIMENT_THRESHOLD = 0.7
ALERT_COOLDOWN = timedelta(hours=1)


def check_and_create_alert(ticker, signal_data: dict) -> AlertFlag | None:
    """
    Creates an AlertFlag if the signal has enough post support and either:
      - hype dampening fired
      - consistency < CONSISTENCY_THRESHOLD

    Alert type:
      - hype_fade if hype dampening fired
      - extreme_sentiment if |sentiment| > EXTREME_SENTIMENT_THRESHOLD
      - divergence otherwise
    """
    consistency = signal_data["consistency"]
    post_count = signal_data["post_count"]
    sentiment = signal_data["sentiment"]
    momentum = signal_data["momentum"]
    hype_dampened = signal_data.get("hype_dampened", False)

    if post_count < MIN_POST_COUNT:
        return None

    if hype_dampened:
        alert_type = AlertFlag.TYPE_HYPE_FADE
    elif consistency >= CONSISTENCY_THRESHOLD:
        return None
    else:
        alert_type = (
            AlertFlag.TYPE_EXTREME
            if abs(sentiment) > EXTREME_SENTIMENT_THRESHOLD
            else AlertFlag.TYPE_DIVERGENCE
        )

    recent_alert_exists = AlertFlag.objects.filter(
        ticker=ticker,
        type=alert_type,
        created_at__gte=timezone.now() - ALERT_COOLDOWN,
    ).exists()
    if recent_alert_exists:
        logger.info("Alert suppressed by cooldown: %s for %s", alert_type, ticker.symbol)
        return None

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
