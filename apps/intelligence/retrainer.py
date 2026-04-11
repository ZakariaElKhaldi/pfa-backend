"""
POST-MVP: Auto-retrain system.

Subscribe to 'accuracy_evaluated' events via event bus.
Track rolling accuracy per ticker (window: last 50 signals).
When accuracy drops below 60%, trigger retrain:
  1. Pull last 90 days of SignalAccuracy + features from signals/ml/features.py
  2. Call signals/ml/trainer.py with new data
  3. Hot-swap model in signals/ml/predictor.py
  4. Log to RetrainLog

Safeguards:
  - Max 1 retrain per ticker per 24h
  - A/B test new model on shadow predictions before promoting
  - Never retrain if < 100 accuracy records exist

Implementation:
  from apps.events.bus import subscribe
  from apps.events.types import ACCURACY_EVALUATED

  def start():
      subscribe(ACCURACY_EVALUATED, handle_accuracy_event)

  def handle_accuracy_event(payload):
      ticker = payload["ticker"]
      # Check rolling accuracy window
      # Trigger retrain if below threshold
      pass
"""
