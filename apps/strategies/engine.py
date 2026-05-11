import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.market.indicators import bollinger_bands, ema, macd, rsi, sma
from apps.market.models import PriceSnapshot
from apps.strategies.models import StrategyExecution, StrategyRule
from apps.tickers.models import Ticker

logger = logging.getLogger(__name__)

SUPPORTED_ACTIONS = {"notify", "email", "webhook", "log"}
NUMERIC_FIELDS = {
    "sentiment_score",
    "rsi",
    "sma_20",
    "ema_50",
    "volume_change",
    "bollinger_position",
    "price",
}
ENUM_FIELDS = {"signal", "alert_type", "mood", "macd_signal"}


@dataclass(frozen=True)
class ConditionResult:
    matched: bool
    field: str
    operator: str
    expected: str
    actual: Any


def evaluate_strategies_for_event(event_type: str, payload: dict[str, Any]) -> list[StrategyExecution]:
    """Evaluate active rules for one market/signal event and persist execution rows."""
    symbol = payload.get("ticker") or payload.get("symbol") or payload.get("ticker_symbol")
    if not symbol:
        return []

    try:
        ticker = Ticker.objects.get(symbol=str(symbol).upper())
    except Ticker.DoesNotExist:
        logger.warning("Strategy event ignored for unknown ticker %s", symbol)
        return []

    context = build_evaluation_context(ticker, payload)
    rules = (
        StrategyRule.objects
        .filter(is_active=True)
        .filter(Q(tickers=ticker) | Q(tickers__isnull=True))
        .distinct()
        .prefetch_related("conditions", "actions", "tickers")
    )

    executions: list[StrategyExecution] = []
    for rule in rules:
        try:
            matched, condition_results = evaluate_rule(rule, context)
            actions_taken = execute_actions(rule, context) if matched else []
            execution = StrategyExecution.objects.create(
                rule=rule,
                event_type=event_type[:30],
                event_data=context,
                conditions_matched=[
                    {
                        "field": result.field,
                        "operator": result.operator,
                        "expected": result.expected,
                        "actual": result.actual,
                    }
                    for result in condition_results
                    if result.matched
                ],
                actions_taken=actions_taken,
                success=True,
            )
        except Exception as exc:
            logger.exception("Strategy %s evaluation failed: %s", rule.pk, exc)
            execution = StrategyExecution.objects.create(
                rule=rule,
                event_type=event_type[:30],
                event_data=context,
                conditions_matched=[],
                actions_taken=[],
                success=False,
            )
        executions.append(execution)
    return executions


def build_evaluation_context(ticker: Ticker, payload: dict[str, Any]) -> dict[str, Any]:
    context = dict(payload)
    context["ticker"] = ticker.symbol

    sentiment = payload.get("sentiment")
    if sentiment is not None:
        context["sentiment_score"] = sentiment
        context["mood"] = _mood_from_sentiment(_to_decimal(sentiment))

    prices = list(
        PriceSnapshot.objects
        .filter(ticker=ticker)
        .order_by("timestamp")
        .values_list("price", "volume")
    )
    if not prices:
        return context

    closes = [float(price) for price, _volume in prices]
    volumes = [int(volume or 0) for _price, volume in prices]
    latest_price = closes[-1]
    context.setdefault("price", latest_price)
    context["sma_20"] = sma(closes, 20)
    context["ema_50"] = ema(closes, 50)
    context["rsi"] = rsi(closes, 14)

    if len(volumes) > 1:
        baseline = sum(volumes[:-1][-20:]) / min(len(volumes) - 1, 20)
        context["volume_change"] = (volumes[-1] - baseline) / baseline if baseline else None
    else:
        context["volume_change"] = None

    bands = bollinger_bands(closes, 20)
    if bands and bands["upper"] != bands["lower"]:
        context["bollinger_position"] = (latest_price - bands["lower"]) / (bands["upper"] - bands["lower"])
    else:
        context["bollinger_position"] = None

    macd_result = macd(closes)
    histogram = macd_result["histogram"] if macd_result else None
    if histogram is not None:
        context["macd_signal"] = "bullish" if histogram > 0 else "bearish" if histogram < 0 else "neutral"
    else:
        context["macd_signal"] = None

    return context


def evaluate_rule(rule: StrategyRule, context: dict[str, Any]) -> tuple[bool, list[ConditionResult]]:
    conditions = list(rule.conditions.all())
    if not conditions:
        return False, []

    results = [_evaluate_condition(condition, context) for condition in conditions]
    matched = results[0].matched
    for index, result in enumerate(results[1:], start=1):
        logical_op = conditions[index].logical_op or "AND"
        if logical_op == "OR":
            matched = matched or result.matched
        else:
            matched = matched and result.matched
    return matched, results


def execute_actions(rule: StrategyRule, context: dict[str, Any]) -> list[str]:
    actions_taken: list[str] = []
    for action in rule.actions.all():
        if action.action_type not in SUPPORTED_ACTIONS:
            raise ValueError(f"Unsupported action: {action.action_type}")
        target = action.config.get("target") or action.config.get("message") or context.get("ticker")
        actions_taken.append(f"{action.action_type}:{target}" if target else action.action_type)
    return actions_taken


def _evaluate_condition(condition, context: dict[str, Any]) -> ConditionResult:
    actual = context.get(condition.field)
    expected = condition.value
    matched = _compare(actual, condition.operator, expected, condition.field)
    return ConditionResult(
        matched=matched,
        field=condition.field,
        operator=condition.operator,
        expected=str(expected),
        actual=actual,
    )


def _compare(actual: Any, operator: str, expected: Any, field: str) -> bool:
    if actual is None:
        return False
    if operator in {"gt", "lt", "gte", "lte"} or field in NUMERIC_FIELDS:
        left = _to_decimal(actual)
        right = _to_decimal(expected)
        if left is None or right is None:
            return False
        if operator == "gt":
            return left > right
        if operator == "lt":
            return left < right
        if operator == "gte":
            return left >= right
        if operator == "lte":
            return left <= right
        if operator == "eq":
            return left == right
        if operator == "neq":
            return left != right
        return False

    left_text = str(actual).strip().lower()
    right_text = str(expected).strip().lower()
    if operator == "eq":
        return left_text == right_text
    if operator == "neq":
        return left_text != right_text
    if operator == "contains":
        return right_text in left_text
    return False


def _to_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _mood_from_sentiment(sentiment: Decimal | None) -> str | None:
    if sentiment is None:
        return None
    if sentiment >= Decimal("0.75"):
        return "euphoric"
    if sentiment >= Decimal("0.2"):
        return "bullish"
    if sentiment <= Decimal("-0.75"):
        return "panic"
    if sentiment <= Decimal("-0.2"):
        return "bearish"
    return "uncertain"


def recent_health(last_execution: StrategyExecution | None, active: bool) -> str:
    if not active:
        return "inactive"
    if last_execution is None:
        return "never_run"
    if not last_execution.success:
        return "failing"
    if last_execution.triggered_at >= timezone.now() - timedelta(minutes=30):
        return "working"
    return "idle"
