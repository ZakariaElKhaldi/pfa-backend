"""
POST-MVP: Market mood memory system.

Subscribe to 'signal_generated' events.
Maintain per-ticker rolling sentiment embedding:
  1. Collect last 6h of SentimentScore values
  2. Compute embedding: [avg_score, std_dev, trend_slope, volume_ratio, source_diversity]
  3. Classify dominant mood: bullish, bearish, uncertain, euphoric, panic
  4. Store as MarketMoodSnapshot

Use mood transitions as signal features:
  - "panic -> euphoric" = potential reversal signal
  - "bullish -> uncertain" = weakening momentum

Feed mood history into retrained XGBoost model as additional features.

Implementation:
  from apps.events.bus import subscribe
  from apps.events.types import SIGNAL_GENERATED

  def start():
      subscribe(SIGNAL_GENERATED, handle_signal_event)

  def handle_signal_event(payload):
      # Build mood snapshot for ticker
      pass
"""
