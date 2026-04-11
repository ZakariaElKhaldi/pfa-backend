"""
POST-MVP: Manipulation detection system.

Subscribe to 'signal_generated' + 'pipeline_completed' events.

Detection signals:
  1. Volume spike: post count > 3x rolling 7-day average
  2. Sentiment uniformity: >90% posts same direction (real crowds are noisy)
  3. Account freshness: >50% posts from accounts < 30 days old (StockTwits)
  4. Timing pattern: >10 posts within 2-minute window with similar phrasing
  5. Price divergence: sentiment 90%+ bullish but price dropping (or vice versa)

When confidence > 0.7, create ManipulationFlag.
Also create AlertFlag with type='manipulation' for Compliance Officer.

Implementation:
  from apps.events.bus import subscribe
  from apps.events.types import SIGNAL_GENERATED, PIPELINE_COMPLETED

  def start():
      subscribe(SIGNAL_GENERATED, handle_signal_event)
      subscribe(PIPELINE_COMPLETED, handle_pipeline_event)
"""
