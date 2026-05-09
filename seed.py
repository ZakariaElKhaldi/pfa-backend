"""
CrowdSignal V2 — comprehensive database seed script.
Run with: python seed.py  (from the pfa-backend directory)
"""
import os, sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

# ── helpers ──────────────────────────────────────────────────────────────────
now = timezone.now()
rnd = random.Random(42)   # deterministic

def days_ago(n, jitter_hours=0):
    return now - timedelta(days=n, hours=rnd.uniform(0, jitter_hours))

def rand_float(lo, hi, decimals=4):
    return round(rnd.uniform(lo, hi), decimals)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ═══════════════════════════════════════════════════════════════════════════
# 1. TICKERS
# ═══════════════════════════════════════════════════════════════════════════
from apps.tickers.models import Ticker, Watchlist
from apps.accounts.models import CustomUser

TICKER_DATA = [
    # Technology
    ("AAPL",  "Apple Inc.",                  "Technology"),
    ("MSFT",  "Microsoft Corp.",             "Technology"),
    ("NVDA",  "NVIDIA Corp.",                "Technology"),
    ("GOOGL", "Alphabet Inc.",               "Technology"),
    ("META",  "Meta Platforms Inc.",         "Technology"),
    ("AMD",   "Advanced Micro Devices",      "Technology"),
    ("INTC",  "Intel Corp.",                 "Technology"),
    ("CRM",   "Salesforce Inc.",             "Technology"),
    ("ORCL",  "Oracle Corp.",                "Technology"),
    ("ADBE",  "Adobe Inc.",                  "Technology"),
    # Consumer
    ("TSLA",  "Tesla Inc.",                  "Consumer Cyclical"),
    ("AMZN",  "Amazon.com Inc.",             "Consumer Cyclical"),
    ("NKE",   "Nike Inc.",                   "Consumer Cyclical"),
    ("SBUX",  "Starbucks Corp.",             "Consumer Cyclical"),
    ("MCD",   "McDonald's Corp.",            "Consumer Defensive"),
    # Finance
    ("JPM",   "JPMorgan Chase & Co.",        "Financial Services"),
    ("BAC",   "Bank of America Corp.",       "Financial Services"),
    ("GS",    "Goldman Sachs Group Inc.",    "Financial Services"),
    ("V",     "Visa Inc.",                   "Financial Services"),
    ("MA",    "Mastercard Inc.",             "Financial Services"),
    # Healthcare
    ("JNJ",   "Johnson & Johnson",           "Healthcare"),
    ("PFE",   "Pfizer Inc.",                 "Healthcare"),
    ("UNH",   "UnitedHealth Group Inc.",     "Healthcare"),
    ("ABBV",  "AbbVie Inc.",                 "Healthcare"),
    # Energy / Industrials
    ("XOM",   "Exxon Mobil Corp.",           "Energy"),
    ("CVX",   "Chevron Corp.",               "Energy"),
    ("BA",    "Boeing Co.",                  "Industrials"),
    ("CAT",   "Caterpillar Inc.",            "Industrials"),
    # Meme / Volatile
    ("GME",   "GameStop Corp.",              "Consumer Cyclical"),
    ("AMC",   "AMC Entertainment Holdings", "Communication Services"),
]

tickers = {}
for symbol, name, sector in TICKER_DATA:
    obj, _ = Ticker.objects.get_or_create(
        symbol=symbol,
        defaults={"name": name, "sector": sector},
    )
    tickers[symbol] = obj

print(f"[tickers] {len(tickers)} tickers ready")

# ═══════════════════════════════════════════════════════════════════════════
# 2. WATCHLIST  (admin user watches 12 tickers)
# ═══════════════════════════════════════════════════════════════════════════
admin = CustomUser.objects.filter(is_superuser=True).first()
watch_symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META",
                 "GOOGL", "AMD", "JPM", "GME", "AMC", "GOOGL"]
for sym in watch_symbols:
    if sym in tickers:
        Watchlist.objects.get_or_create(user=admin, ticker=tickers[sym])

print(f"[watchlist] populated for {admin.email}")

# ═══════════════════════════════════════════════════════════════════════════
# 3. PRICE SNAPSHOTS  (60 days, every 4 hours)
# ═══════════════════════════════════════════════════════════════════════════
from apps.market.models import PriceSnapshot

BASE_PRICES = {
    "AAPL": 178, "MSFT": 415, "NVDA": 880, "GOOGL": 172, "META": 505,
    "AMD":  165, "INTC":  30, "CRM":  295, "ORCL":  125, "ADBE": 470,
    "TSLA": 175, "AMZN":  195, "NKE":   94, "SBUX":   78, "MCD":  290,
    "JPM":  198, "BAC":    38, "GS":   460, "V":      275, "MA":   470,
    "JNJ":  152, "PFE":    26, "UNH":  520, "ABBV":  168, "XOM":  115,
    "CVX":  155, "BA":     175, "CAT":  360, "GME":    15, "AMC":    4,
}

price_objs = []
for sym, ticker_obj in tickers.items():
    base = BASE_PRICES.get(sym, 100)
    price = float(base)
    for day in range(60, 0, -1):
        for hour_offset in [0, 4, 8, 12, 16, 20]:
            ts = now - timedelta(days=day, hours=hour_offset)
            change = rnd.gauss(0, 0.008)   # 0.8 % std-dev per bar
            price = max(0.5, price * (1 + change))
            o = price * (1 + rnd.gauss(0, 0.002))
            h = price * (1 + abs(rnd.gauss(0, 0.004)))
            l = price * (1 - abs(rnd.gauss(0, 0.004)))
            vol = int(rnd.uniform(500_000, 50_000_000))
            price_objs.append(PriceSnapshot(
                ticker=ticker_obj,
                price=Decimal(str(round(price, 4))),
                open_price=Decimal(str(round(o, 4))),
                high_price=Decimal(str(round(h, 4))),
                low_price=Decimal(str(round(l, 4))),
                volume=vol,
                timestamp=ts,
            ))

PriceSnapshot.objects.bulk_create(price_objs, ignore_conflicts=True)
print(f"[prices] {len(price_objs)} price snapshots created")

# ═══════════════════════════════════════════════════════════════════════════
# 4. SOCIAL POSTS
# ═══════════════════════════════════════════════════════════════════════════
from apps.social.models import SocialPost

BULLISH_TITLES = [
    "This is going to the moon!", "Strong buy signal here", "Earnings beat incoming",
    "Huge institutional buying detected", "Breaking out of resistance",
    "All indicators green — time to load up", "Short squeeze incoming",
    "Analyst upgrades — price target raised", "Record revenue incoming",
    "Options flow extremely bullish this week",
]
BEARISH_TITLES = [
    "Massive red flags — avoid", "Short this now", "Earnings miss incoming",
    "CEO just dumped shares", "Breaking down from support",
    "Death cross forming on the daily", "Revenue guidance slashed",
    "Macro headwinds will crush this sector", "Insiders selling aggressively",
    "This is a value trap — get out",
]
NEUTRAL_TITLES = [
    "Weekly analysis thread", "What's your price target?",
    "Comparing Q3 vs Q4 earnings", "Sector rotation thoughts",
    "Risk/reward at current levels", "Technical levels to watch",
    "Volume analysis for the week", "Holding through earnings?",
    "Average down or cut losses?", "Market open watchlist",
]
BULLISH_CONTENT = [
    "The technicals are screaming buy. RSI just bounced off oversold territory and volume is picking up.",
    "Huge call buying this morning. Someone knows something. Loading up here.",
    "Management has been executing flawlessly. The market is sleeping on this one.",
    "Fundamentals are rock solid. Free cash flow growing 25% YoY. This is a no-brainer.",
    "Just added 200 shares. The pullback was a gift. Next stop ATH.",
]
BEARISH_CONTENT = [
    "The chart is broken. Lower highs, lower lows. Classic distribution pattern.",
    "Revenue growth is decelerating. Margins are compressing. Multiple will contract.",
    "Debt load is unsustainable at these rates. Refinancing risk is real.",
    "Competition is intensifying. Market share erosion is accelerating.",
    "Insiders have sold $50M worth of stock in the last 30 days. Red flag.",
]
NEUTRAL_CONTENT = [
    "Holding a small position. Waiting for the next catalyst before adding.",
    "Interesting setup but I need to see volume confirm the breakout.",
    "Fair value at current levels. Neither a strong buy nor a sell.",
    "Earnings in 2 weeks. Implied volatility is elevated. Selling premium.",
    "The sector is mixed. Some names look good, others are stretched.",
]

SOURCES = ["reddit", "stocktwits"]

post_objs = []
used_ids = set()
for sym, ticker_obj in tickers.items():
    n_posts = rnd.randint(30, 80)
    for i in range(n_posts):
        label = rnd.choices(["bullish", "bearish", "neutral"], weights=[45, 30, 25])[0]
        if label == "bullish":
            title   = rnd.choice(BULLISH_TITLES)
            content = rnd.choice(BULLISH_CONTENT)
            score   = rand_float(0.35, 0.95, 4)
            pos, neg, neu = rand_float(0.5, 0.95), rand_float(0.02, 0.2), rand_float(0.02, 0.2)
        elif label == "bearish":
            title   = rnd.choice(BEARISH_TITLES)
            content = rnd.choice(BEARISH_CONTENT)
            score   = rand_float(-0.95, -0.25, 4)
            pos, neg, neu = rand_float(0.02, 0.2), rand_float(0.5, 0.95), rand_float(0.02, 0.2)
        else:
            title   = rnd.choice(NEUTRAL_TITLES)
            content = rnd.choice(NEUTRAL_CONTENT)
            score   = rand_float(-0.2, 0.2, 4)
            pos, neg, neu = rand_float(0.2, 0.4), rand_float(0.2, 0.4), rand_float(0.3, 0.6)

        source = rnd.choice(SOURCES)
        ext_id = f"{sym}-{source}-{uuid.uuid4().hex[:12]}"
        posted = days_ago(rnd.randint(0, 59), jitter_hours=23)

        post_objs.append(SocialPost(
            ticker=ticker_obj,
            source=source,
            external_id=ext_id,
            title=f"${sym}: {title}",
            content=f"${sym} — {content}",
            sentiment_score=score,
            sentiment_label=label,
            positive_prob=round(clamp(pos, 0, 1), 4),
            negative_prob=round(clamp(neg, 0, 1), 4),
            neutral_prob=round(clamp(neu, 0, 1), 4),
            posted_at=posted,
            fetched_at=posted,
        ))

# bypass auto_now_add so our historical posted_at/fetched_at are used
for f in SocialPost._meta.local_fields:
    if f.name in ("fetched_at",):
        f.auto_now_add = False
SocialPost.objects.bulk_create(post_objs, ignore_conflicts=True)
for f in SocialPost._meta.local_fields:
    if f.name in ("fetched_at",):
        f.auto_now_add = True
print(f"[social] {len(post_objs)} posts created")

# ═══════════════════════════════════════════════════════════════════════════
# 5. SIGNAL SNAPSHOTS + ACCURACY + DECISION LOGS
# ═══════════════════════════════════════════════════════════════════════════
from apps.signals.models import AlertFlag, DecisionLog, SignalAccuracy, SignalSnapshot

METHODS = ["rule_based", "xgboost", "ensemble"]

snapshots = []
for sym, ticker_obj in tickers.items():
    sentiment_bias = rnd.gauss(0.1, 0.3)   # per-ticker bias
    for day in range(60, 0, -1):
        # 2–4 snapshots per day
        for _ in range(rnd.randint(2, 4)):
            ts = days_ago(day, jitter_hours=22)
            sentiment = clamp(rnd.gauss(sentiment_bias, 0.25), -1, 1)
            momentum  = clamp(rnd.gauss(0, 0.35), -1, 1)
            consist   = clamp(abs(rnd.gauss(0.5, 0.2)), 0, 1)
            total     = rnd.randint(15, 200)
            pos_c     = int(total * clamp(rnd.gauss(0.45, 0.2), 0, 1))
            neg_c     = int(total * clamp(rnd.gauss(0.3, 0.15), 0, 1))
            neu_c     = total - pos_c - neg_c
            br        = round(clamp(pos_c / max(total, 1), 0, 1), 4)

            if sentiment > 0.3 and momentum > 0.1:
                signal = "BUY"
            elif sentiment < -0.25 or momentum < -0.25:
                signal = "SELL"
            else:
                signal = "HOLD"

            method = rnd.choice(METHODS)
            conf   = rand_float(0.52, 0.96) if method != "rule_based" else None

            snapshots.append(SignalSnapshot(
                ticker=ticker_obj,
                sentiment=round(sentiment, 4),
                momentum=round(momentum, 4),
                consistency=round(consist, 4),
                signal=signal,
                post_count=total,
                bullish_ratio=br,
                normalized_index=round(clamp(sentiment * 0.5 + momentum * 0.3 + consist * 0.2, -1, 1), 4),
                time_decay_score=round(rand_float(0.3, 0.9), 4),
                source_weighted_score=round(rand_float(0.3, 0.9), 4),
                positive_count=max(0, pos_c),
                negative_count=max(0, neg_c),
                neutral_count=max(0, neu_c),
                prediction_method=method,
                prediction_confidence=conf,
                feature_importances={"sentiment": 0.4, "momentum": 0.35, "consistency": 0.25} if method != "rule_based" else None,
                created_at=ts,
            ))

for f in SignalSnapshot._meta.local_fields:
    if f.name == "created_at":
        f.auto_now_add = False
SignalSnapshot.objects.bulk_create(snapshots)
for f in SignalSnapshot._meta.local_fields:
    if f.name == "created_at":
        f.auto_now_add = True
print(f"[signals] {len(snapshots)} snapshots created")

# Accuracy records for older snapshots (> 24 h old)
all_snaps = SignalSnapshot.objects.filter(
    created_at__lt=now - timedelta(hours=25)
).select_related("ticker")

accuracy_objs = []
decision_objs = []
base_prices_dec = {sym: Decimal(str(BASE_PRICES.get(sym, 100))) for sym in tickers}

for snap in all_snaps:
    sym = snap.ticker.symbol
    base = float(base_prices_dec.get(sym, 100))
    p0   = Decimal(str(round(base * rnd.uniform(0.85, 1.15), 4)))
    p1h  = p0 * Decimal(str(1 + rnd.gauss(0, 0.008)))
    p24h = p0 * Decimal(str(1 + rnd.gauss(0, 0.02)))

    if snap.signal == "BUY":
        correct_24h = float(p24h) > float(p0)
    elif snap.signal == "SELL":
        correct_24h = float(p24h) < float(p0)
    else:
        correct_24h = abs(float(p24h) - float(p0)) / float(p0) < 0.01

    direction = "UP" if float(p24h) > float(p0) else ("DOWN" if float(p24h) < float(p0) else "FLAT")

    accuracy_objs.append(SignalAccuracy(
        signal_snapshot=snap,
        predicted=snap.signal,
        actual_direction=direction,
        price_at_signal=p0,
        price_after_1h=p1h.quantize(Decimal("0.0001")),
        price_after_24h=p24h.quantize(Decimal("0.0001")),
        accuracy_1h=rnd.random() > 0.4,
        accuracy_24h=correct_24h,
        evaluated_at=snap.created_at + timedelta(hours=25),
    ))

    decision_objs.append(DecisionLog(
        signal_snapshot=snap,
        ticker=snap.ticker,
        timestamp=snap.created_at,
        input_summary={
            "sentiment": snap.sentiment, "momentum": snap.momentum,
            "consistency": snap.consistency, "post_count": snap.post_count,
        },
        scoring_detail={
            "rule_score": round(snap.sentiment * 0.5 + snap.momentum * 0.5, 4),
            "ml_confidence": snap.prediction_confidence,
            "method": snap.prediction_method,
        },
        engine_output={"signal": snap.signal, "confidence": snap.prediction_confidence},
        alerts_triggered=[],
    ))

SignalAccuracy.objects.bulk_create(accuracy_objs, ignore_conflicts=True)
DecisionLog.objects.bulk_create(decision_objs, ignore_conflicts=True)
print(f"[accuracy] {len(accuracy_objs)} records  |  [decisions] {len(decision_objs)} logs")

# ═══════════════════════════════════════════════════════════════════════════
# 6. ALERT FLAGS
# ═══════════════════════════════════════════════════════════════════════════
ALERT_TYPES = ["divergence", "extreme_sentiment", "hype_fade", "pump_suspected"]
alert_objs = []
for sym in ["GME", "AMC", "TSLA", "NVDA", "META", "AAPL", "AMD", "MSFT",
            "INTC", "PFE", "BA", "XOM"]:
    ticker_obj = tickers.get(sym)
    if not ticker_obj:
        continue
    n = rnd.randint(2, 5)
    for _ in range(n):
        alert_objs.append(AlertFlag(
            ticker=ticker_obj,
            type=rnd.choice(ALERT_TYPES),
            sentiment=rand_float(-1, 1),
            momentum=rand_float(-1, 1),
            consistency=rand_float(0, 1),
            resolved=rnd.random() < 0.35,
            created_at=days_ago(rnd.randint(0, 30), jitter_hours=20),
        ))

AlertFlag.objects.bulk_create(alert_objs)
print(f"[alerts] {len(alert_objs)} alert flags created")

# ═══════════════════════════════════════════════════════════════════════════
# 7. MARKET MOOD SNAPSHOTS
# ═══════════════════════════════════════════════════════════════════════════
from apps.intelligence.models import ManipulationFlag, MarketMoodSnapshot, RetrainLog

MOODS = ["bullish", "bearish", "uncertain", "euphoric", "panic"]
mood_objs = []
for sym, ticker_obj in tickers.items():
    for day in range(30, 0, -3):
        w_start = days_ago(day + 3)
        w_end   = days_ago(day)
        mood_objs.append(MarketMoodSnapshot(
            ticker=ticker_obj,
            embedding=[round(rnd.gauss(0, 1), 4) for _ in range(8)],
            dominant_mood=rnd.choice(MOODS),
            confidence=rand_float(0.55, 0.97),
            window_start=w_start,
            window_end=w_end,
            created_at=w_end,
        ))

MarketMoodSnapshot.objects.bulk_create(mood_objs)
print(f"[mood] {len(mood_objs)} mood snapshots created")

# Manipulation flags
manip_objs = []
for sym in ["GME", "AMC", "TSLA", "NVDA"]:
    ticker_obj = tickers.get(sym)
    if not ticker_obj:
        continue
    for _ in range(rnd.randint(1, 3)):
        manip_objs.append(ManipulationFlag(
            ticker=ticker_obj,
            pattern_type=rnd.choice(["bot_swarm", "pump_dump", "coordinated_spam"]),
            confidence=rand_float(0.6, 0.98),
            evidence={"post_velocity": rnd.randint(50, 500), "unique_accounts": rnd.randint(10, 100)},
            reviewed=rnd.random() < 0.4,
            detected_at=days_ago(rnd.randint(0, 20), jitter_hours=18),
        ))

ManipulationFlag.objects.bulk_create(manip_objs)

# Retrain logs
retrain_objs = []
for sym, ticker_obj in list(tickers.items())[:10]:
    for i in range(rnd.randint(2, 5)):
        started = days_ago(rnd.randint(2, 30))
        retrain_objs.append(RetrainLog(
            ticker=ticker_obj,
            trigger_reason=rnd.choice(["accuracy_drift", "data_volume", "scheduled", "manual"]),
            old_accuracy=rand_float(0.48, 0.72),
            new_accuracy=rand_float(0.62, 0.88),
            model_version=f"v1.{rnd.randint(0,9)}.{rnd.randint(0,9)}",
            training_samples=rnd.randint(500, 5000),
            started_at=started,
            completed_at=started + timedelta(minutes=rnd.randint(5, 45)),
            status="success",
        ))

RetrainLog.objects.bulk_create(retrain_objs)
print(f"[intelligence] {len(manip_objs)} flags  |  {len(retrain_objs)} retrain logs")

# ═══════════════════════════════════════════════════════════════════════════
# 8. PORTFOLIO + TRADES
# ═══════════════════════════════════════════════════════════════════════════
from apps.portfolio.models import Portfolio, Position, Trade

portfolio, _ = Portfolio.objects.get_or_create(
    user=admin,
    defaults={"cash": Decimal("75000.00")},
)

TRADE_PLAN = [
    ("AAPL",  "buy",  50,  172.50),
    ("MSFT",  "buy",  20,  408.00),
    ("NVDA",  "buy",  15,  845.00),
    ("TSLA",  "buy",  40,  168.00),
    ("AMZN",  "buy",  25,  188.00),
    ("META",  "buy",  10,  492.00),
    ("AMD",   "buy",  60,  158.00),
    ("GME",   "buy", 200,   14.20),
    ("AMC",   "buy", 500,    3.80),
    ("JPM",   "buy",  30,  192.00),
    ("AAPL",  "sell", 20,  179.00),
    ("TSLA",  "sell", 15,  182.00),
    ("GME",   "sell", 100,  16.50),
    ("NVDA",  "buy",   5,  892.00),
    ("GOOGL", "buy",  12,  169.00),
]

for i, (sym, side, qty, price) in enumerate(TRADE_PLAN):
    ticker_obj = tickers.get(sym)
    if not ticker_obj:
        continue
    trade = Trade(
        portfolio=portfolio,
        ticker=ticker_obj,
        side=side,
        quantity=qty,
        price=Decimal(str(price)),
    )
    trade.save()

    # Update / create position
    pos, _ = Position.objects.get_or_create(
        portfolio=portfolio, ticker=ticker_obj,
        defaults={"quantity": 0, "avg_price": Decimal("0")},
    )
    if side == "buy":
        total_cost = pos.avg_price * pos.quantity + Decimal(str(price)) * qty
        pos.quantity += qty
        pos.avg_price = (total_cost / pos.quantity).quantize(Decimal("0.0001")) if pos.quantity else Decimal("0")
    else:
        pos.quantity = max(0, pos.quantity - qty)
    pos.save()

print(f"[portfolio] {len(TRADE_PLAN)} trades, {Position.objects.filter(portfolio=portfolio).count()} positions")

# ═══════════════════════════════════════════════════════════════════════════
# 9. STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════
from apps.strategies.models import RuleAction, RuleCondition, StrategyExecution, StrategyRule

STRATEGY_DEFS = [
    {
        "name": "Bullish Momentum Catcher",
        "description": "Triggers when sentiment is strongly positive and momentum confirms.",
        "is_active": True,
        "tickers": ["AAPL", "MSFT", "NVDA", "TSLA"],
        "conditions": [
            ("sentiment_score", "gte", "0.4", "AND"),
            ("signal", "eq", "BUY", "AND"),
        ],
        "actions": [("notify", {"message": "BUY signal confirmed"}), ("log", {})],
    },
    {
        "name": "Bearish Reversal Alert",
        "description": "Fires when momentum crosses below zero after a bullish run.",
        "is_active": True,
        "tickers": ["GME", "AMC", "TSLA"],
        "conditions": [
            ("signal", "eq", "SELL", "AND"),
            ("sentiment_score", "lte", "-0.2", "AND"),
        ],
        "actions": [("notify", {"message": "SELL signal — consider reducing exposure"}), ("email", {})],
    },
    {
        "name": "Extreme Sentiment Watchdog",
        "description": "Alerts when crowd sentiment is euphoric or in panic territory.",
        "is_active": True,
        "tickers": ["NVDA", "META", "AAPL", "AMD"],
        "conditions": [
            ("sentiment_score", "gte", "0.8", "OR"),
            ("sentiment_score", "lte", "-0.8", "OR"),
        ],
        "actions": [("notify", {"message": "Extreme sentiment detected — risk management alert"}), ("log", {})],
    },
    {
        "name": "Volume Spike Detector",
        "description": "Watches for abnormal volume that may precede large moves.",
        "is_active": False,
        "tickers": ["AAPL", "MSFT", "AMZN"],
        "conditions": [
            ("volume_change", "gte", "2.5", "AND"),
        ],
        "actions": [("log", {"detail": "volume_spike"})],
    },
    {
        "name": "RSI Oversold Bounce",
        "description": "Buys dips when RSI is oversold and sentiment starts recovering.",
        "is_active": False,
        "tickers": ["AAPL", "GOOGL", "JPM"],
        "conditions": [
            ("rsi", "lte", "30", "AND"),
            ("sentiment_score", "gte", "0.0", "AND"),
        ],
        "actions": [("notify", {"message": "RSI oversold + positive sentiment — potential bounce"}), ("log", {})],
    },
]

for sdef in STRATEGY_DEFS:
    rule, created = StrategyRule.objects.get_or_create(
        user=admin, name=sdef["name"],
        defaults={"description": sdef["description"], "is_active": sdef["is_active"]},
    )
    if created:
        rule.tickers.set([tickers[s] for s in sdef["tickers"] if s in tickers])
        for order, (field, op, val, logical) in enumerate(sdef["conditions"]):
            RuleCondition.objects.create(
                rule=rule, field=field, operator=op,
                value=val, logical_op=logical, order=order,
            )
        for order, (atype, config) in enumerate(sdef["actions"]):
            RuleAction.objects.create(rule=rule, action_type=atype, config=config, order=order)

        # seed 5–15 executions per active strategy
        if sdef["is_active"]:
            for _ in range(rnd.randint(5, 15)):
                sym = rnd.choice(sdef["tickers"])
                StrategyExecution.objects.create(
                    rule=rule,
                    triggered_at=days_ago(rnd.randint(0, 30), jitter_hours=20),
                    event_type="signal_update",
                    event_data={"ticker": sym, "signal": rnd.choice(["BUY", "SELL", "HOLD"])},
                    conditions_matched=[c[0] for c in sdef["conditions"]],
                    actions_taken=[a[0] for a in sdef["actions"]],
                    success=rnd.random() > 0.05,
                )

print(f"[strategies] {StrategyRule.objects.filter(user=admin).count()} strategies seeded")

# ═══════════════════════════════════════════════════════════════════════════
# 10. BACKTEST RUNS
# ═══════════════════════════════════════════════════════════════════════════
from apps.analytics.models import BacktestRun

for sym in ["AAPL", "TSLA", "NVDA", "GME", "MSFT", "META", "AMD"]:
    ticker_obj = tickers.get(sym)
    if not ticker_obj:
        continue
    for strategy in ["signal", "sentiment_threshold"]:
        w_start = days_ago(60)
        w_end   = days_ago(5)
        win_rate = rand_float(0.38, 0.72)
        BacktestRun.objects.create(
            user=admin,
            ticker=ticker_obj,
            strategy=strategy,
            params={"threshold": 0.35} if strategy == "sentiment_threshold" else {},
            window_start=w_start,
            window_end=w_end,
            win_rate=win_rate,
            sharpe=rand_float(-0.5, 2.8),
            max_drawdown=rand_float(-0.35, -0.03),
            total_return=rand_float(-0.25, 0.85),
            trades=[
                {"day": i, "side": rnd.choice(["buy", "sell"]), "price": rand_float(50, 500)}
                for i in range(rnd.randint(8, 30))
            ],
            equity_curve=[round(1.0 + rnd.gauss(0, 0.015) * i, 4) for i in range(55)],
            status="ok",
        )

print(f"[analytics] {BacktestRun.objects.filter(user=admin).count()} backtest runs created")

# ═══════════════════════════════════════════════════════════════════════════
# 11. USER PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════
from apps.accounts.models import UserPreference

UserPreference.objects.get_or_create(
    user=admin,
    defaults={
        "theme": "dark",
        "default_ticker": "AAPL",
        "alert_email": True,
        "alert_push": True,
        "digest_frequency": "daily",
    },
)
print("[preferences] admin preferences set")

# ═══════════════════════════════════════════════════════════════════════════
print("\nSeed complete!")
counts = {
    "tickers":     Ticker.objects.count(),
    "social_posts": SocialPost.objects.count(),
    "signals":     SignalSnapshot.objects.count(),
    "accuracy":    SignalAccuracy.objects.count(),
    "alerts":      AlertFlag.objects.count(),
    "prices":      PriceSnapshot.objects.count(),
    "strategies":  StrategyRule.objects.count(),
    "backtests":   BacktestRun.objects.count(),
    "mood":        MarketMoodSnapshot.objects.count(),
    "trades":      Trade.objects.count(),
}
for k, v in counts.items():
    print(f"  {k:<15} {v:>6}")
