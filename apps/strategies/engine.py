"""
POST-MVP: Strategy execution engine.

Run as Celery worker subscribing to event bus.
On each event (signal_generated, price_updated, alert_created):
  1. Find all active StrategyRules that watch the event's ticker (or all tickers)
  2. Evaluate conditions against event data + current market state
  3. For matched rules, execute actions in order
  4. Log to StrategyExecution

Rate limit: max 1 execution per rule per 5 minutes (prevent spam)

Safeguards:
  - auto_trade action requires explicit user confirmation
  - webhook delivery with retry (3 attempts, exponential backoff)
  - Execution timeout: 30s per rule evaluation

Implementation:
  from apps.events.bus import subscribe
  from apps.events.types import SIGNAL_GENERATED, PRICE_UPDATED, ALERT_CREATED

  def start():
      subscribe(SIGNAL_GENERATED, handle_event)
      subscribe(PRICE_UPDATED, handle_event)
      subscribe(ALERT_CREATED, handle_event)

  def handle_event(payload):
      ticker = payload.get("ticker")
      rules = StrategyRule.objects.filter(
          is_active=True
      ).filter(
          Q(tickers__symbol=ticker) | Q(tickers__isnull=True)
      )
      for rule in rules:
          if evaluate_conditions(rule, payload):
              execute_actions(rule, payload)

POST-MVP: Visual rule builder frontend
  - Drag-and-drop condition builder in React
  - Backtesting: "if this rule existed last 30 days, what would have triggered?"
  - Execution timeline visualization
"""
