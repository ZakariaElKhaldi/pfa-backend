import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from django.utils import timezone
from datetime import timedelta

# --- FinBERT / Sentiment pipeline ---
print("\n=== SENTIMENT MODEL (FinBERT) ===")
try:
    from apps.sentiment.scoring import SentimentScorer
    scorer = SentimentScorer()
    test_texts = [
        "Apple stock is absolutely crushing it, huge bullish momentum!",
        "Tesla is collapsing, serious sell-off incoming.",
        "Markets are flat today, no major moves.",
    ]
    results = scorer.score_batch(test_texts)
    print("  FinBERT loaded and scoring OK:")
    for text, res in zip(test_texts, results):
        lbl = res.get('label', res.get('sentiment', '?'))
        pos = res.get('positive', res.get('pos', 0))
        neg = res.get('negative', res.get('neg', 0))
        neu = res.get('neutral',  res.get('neu', 0))
        print(f"    [{str(lbl):10}] pos={float(pos):.2f} neg={float(neg):.2f} neu={float(neu):.2f}  \"{text[:55]}\"")
except Exception as e:
    print(f"  ERROR loading/running FinBERT: {e}")

# --- Signal Engine ---
print("\n=== SIGNAL ENGINE ===")
try:
    from apps.signals.engine import SignalEngine
    engine = SignalEngine()
    print("  SignalEngine instantiated OK")
    from apps.tickers.models import Ticker
    ticker = Ticker.objects.first()
    if ticker:
        result = engine.compute(ticker)
        print(f"  compute({ticker.symbol}) => signal={result.get('signal')}  method={result.get('prediction_method')}  post_count={result.get('post_count')}  sentiment={result.get('sentiment')}")
    else:
        print("  No tickers to test against")
except Exception as e:
    import traceback
    print(f"  ERROR: {e}")
    traceback.print_exc()

# --- XGBoost ML predictor ---
print("\n=== ML PREDICTOR (XGBoost) ===")
try:
    from apps.signals.ml.predictor import MLPredictor
    predictor = MLPredictor()
    model_attr = getattr(predictor, 'model', None) or getattr(predictor, '_model', None)
    loaded = model_attr is not None
    print(f"  MLPredictor instantiated OK  |  model_loaded={loaded}")
    if not loaded:
        print("  (No trained model file found — will fall back to rule-based engine)")
except Exception as e:
    print(f"  ERROR: {e}")

# --- Signal Accuracy ---
from apps.signals.models import SignalAccuracy
total_acc    = SignalAccuracy.objects.count()
accurate_1h  = SignalAccuracy.objects.filter(accuracy_1h=True).count()
accurate_24h = SignalAccuracy.objects.filter(accuracy_24h=True).count()
print(f"\n=== SIGNAL ACCURACY ===")
print(f"  Total evaluated: {total_acc}")
if total_acc:
    print(f"  Accurate (1h):   {accurate_1h}/{total_acc}  ({100*accurate_1h//total_acc}%)")
    print(f"  Accurate (24h):  {accurate_24h}/{total_acc}  ({100*accurate_24h//total_acc}%)")
else:
    print("  No accuracy records yet")

# --- Alert Flags ---
from apps.signals.models import AlertFlag
from django.db.models import Count
total_alerts = AlertFlag.objects.count()
unresolved   = AlertFlag.objects.filter(resolved=False).count()
print(f"\n=== ALERT FLAGS ===")
print(f"  Total:      {total_alerts}")
print(f"  Unresolved: {unresolved}")
if total_alerts:
    by_type = AlertFlag.objects.values("type").annotate(n=Count("id")).order_by("-n")
    for row in by_type:
        print(f"    {row['type']:28} {row['n']}")

# --- Decision Logs ---
from apps.signals.models import DecisionLog
total_logs = DecisionLog.objects.count()
print(f"\n=== DECISION LOGS ===")
print(f"  Total audit entries: {total_logs}")
last_log = DecisionLog.objects.order_by("-timestamp").first()
if last_log:
    print(f"  Most recent: {last_log.timestamp}  ticker={last_log.ticker.symbol}")
    print(f"  Engine output: {str(last_log.engine_output)[:120]}")
