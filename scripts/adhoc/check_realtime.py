import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from django.utils import timezone
from datetime import timedelta
import redis as redis_lib

# ── 1. REDIS CONNECTIVITY ────────────────────────────────────────────────────
print("\n=== REDIS ===")
try:
    r = redis_lib.Redis(host="localhost", port=6379, db=0, socket_connect_timeout=3)
    pong = r.ping()
    print(f"  Connection:   OK (PING={pong})")

    # Celery queue depths
    for queue in ("celery", "default"):
        depth = r.llen(queue)
        print(f"  Queue '{queue}': {depth} pending tasks")

    # Active Celery workers registered in Redis
    worker_keys = r.keys("celery@*")
    inspect_keys = r.keys("_kombu*") or r.keys("kombu*")
    print(f"  Worker heartbeat keys: {len(worker_keys)}")

    # Channel layer keys (Django Channels)
    channel_keys = r.keys("asgi*")
    print(f"  Channels layer keys:   {len(channel_keys)}")

    # All key namespaces for overview
    all_keys = r.keys("*")
    namespaces = {}
    for k in all_keys:
        ns = k.decode().split(":")[0].split(".")[0][:20]
        namespaces[ns] = namespaces.get(ns, 0) + 1
    print(f"  Key namespaces ({len(all_keys)} total keys):")
    for ns, count in sorted(namespaces.items(), key=lambda x: -x[1])[:15]:
        print(f"    {ns:25} {count}")
except Exception as e:
    print(f"  ERROR: {e}")

# ── 2. CELERY BEAT / WORKER STATUS ───────────────────────────────────────────
print("\n=== CELERY BEAT SCHEDULE (from settings) ===")
try:
    from django.conf import settings
    schedule = getattr(settings, "CELERY_BEAT_SCHEDULE", {})
    if schedule:
        for name, cfg in schedule.items():
            task = cfg.get("task", "?")
            every = cfg.get("schedule", "?")
            print(f"  {name:45} every {every}")
    else:
        print("  No CELERY_BEAT_SCHEDULE found in settings")
except Exception as e:
    print(f"  ERROR: {e}")

# ── 3. DATA FRESHNESS PER TICKER ─────────────────────────────────────────────
print("\n=== DATA FRESHNESS PER TICKER ===")
from apps.tickers.models import Ticker
from apps.social.models import SocialPost
from apps.signals.models import SignalSnapshot
from apps.market.models import PriceSnapshot

now = timezone.now()
tickers = Ticker.objects.all().order_by("symbol")

print(f"  {'TICKER':<7} {'LAST SIGNAL':>22}  {'LAST POST':>22}  {'LAST PRICE':>22}  SIGNAL")
print(f"  {'-'*7}  {'-'*22}  {'-'*22}  {'-'*22}  {'-'*6}")

all_stale = True
for t in tickers:
    sig   = SignalSnapshot.objects.filter(ticker=t).order_by("-created_at").first()
    post  = SocialPost.objects.filter(ticker=t).order_by("-fetched_at").first()
    price = PriceSnapshot.objects.filter(ticker=t).order_by("-timestamp").first()

    def fmt(dt):
        if not dt: return "NONE"
        age = now - dt
        h = int(age.total_seconds() // 3600)
        m = int((age.total_seconds() % 3600) // 60)
        return f"{h}h{m:02d}m ago"

    sig_age   = fmt(sig.created_at if sig else None)
    post_age  = fmt(post.fetched_at if post else None)
    price_age = fmt(price.timestamp if price else None)
    sig_val   = sig.signal if sig else "NONE"

    # flag if any data is older than 1 hour
    stale = []
    if sig and (now - sig.created_at) > timedelta(hours=1):   stale.append("SIG")
    if post and (now - post.fetched_at) > timedelta(hours=1): stale.append("POST")
    if price and (now - price.timestamp) > timedelta(hours=1):stale.append("PRICE")
    if not stale: all_stale = False

    flag = " [STALE: " + "+".join(stale) + "]" if stale else " [FRESH]"
    print(f"  {t.symbol:<7} {sig_age:>22}  {post_age:>22}  {price_age:>22}  {sig_val:<6}{flag}")

# ── 4. PIPELINE LAST RUN SUMMARY ─────────────────────────────────────────────
print("\n=== PIPELINE LAST RUN ===")
last_sig   = SignalSnapshot.objects.order_by("-created_at").first()
last_post  = SocialPost.objects.order_by("-fetched_at").first()
last_price = PriceSnapshot.objects.order_by("-timestamp").first()
print(f"  Last signal generated: {last_sig.created_at if last_sig else 'NONE'}")
print(f"  Last social post:      {last_post.fetched_at if last_post else 'NONE'}")
print(f"  Last price snapshot:   {last_price.timestamp if last_price else 'NONE'}")

# Time since last pipeline run (use signal as proxy)
if last_sig:
    gap = now - last_sig.created_at
    mins = int(gap.total_seconds() // 60)
    expected = 15  # pipeline runs every 15 min
    if mins > expected:
        print(f"  [WARNING] Pipeline last ran {mins}m ago — expected every {expected}m. Celery beat may NOT be running.")
    else:
        print(f"  [OK] Pipeline ran {mins}m ago — within the 15-min schedule.")
