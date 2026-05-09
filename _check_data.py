import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from django.utils import timezone
from datetime import timedelta

# --- Tickers ---
from apps.tickers.models import Ticker
tickers = list(Ticker.objects.all().values("symbol", "name", "sector"))
print(f"\n=== TICKERS ({len(tickers)}) ===")
for t in tickers:
    print(f"  {t['symbol']:8} {t['name'][:30]:30} [{t['sector']}]")

# --- Social Posts ---
from apps.social.models import SocialPost
total_posts = SocialPost.objects.count()
posts_24h   = SocialPost.objects.filter(fetched_at__gte=timezone.now()-timedelta(hours=24)).count()
posts_1h    = SocialPost.objects.filter(fetched_at__gte=timezone.now()-timedelta(hours=1)).count()
last_post   = SocialPost.objects.order_by("-fetched_at").first()
print(f"\n=== SOCIAL POSTS ===")
print(f"  Total:       {total_posts}")
print(f"  Last 24h:    {posts_24h}")
print(f"  Last 1h:     {posts_1h}")
if last_post:
    print(f"  Most recent: {last_post.fetched_at}  source={last_post.source}  ticker={last_post.ticker.symbol if last_post.ticker else 'N/A'}")
else:
    print("  No posts in DB")

# --- Signals ---
from apps.signals.models import SignalSnapshot
total_sigs = SignalSnapshot.objects.count()
sigs_24h   = SignalSnapshot.objects.filter(created_at__gte=timezone.now()-timedelta(hours=24)).count()
sigs_1h    = SignalSnapshot.objects.filter(created_at__gte=timezone.now()-timedelta(hours=1)).count()
last_sig   = SignalSnapshot.objects.order_by("-created_at").first()
print(f"\n=== SIGNAL SNAPSHOTS ===")
print(f"  Total:       {total_sigs}")
print(f"  Last 24h:    {sigs_24h}")
print(f"  Last 1h:     {sigs_1h}")
if last_sig:
    age = timezone.now() - last_sig.created_at
    print(f"  Most recent: {last_sig.created_at}  ticker={last_sig.ticker.symbol}  signal={last_sig.signal}  method={last_sig.prediction_method}  age={int(age.total_seconds()//60)}m")
else:
    print("  No signals in DB")

# --- Price Snapshots ---
from apps.market.models import PriceSnapshot
total_prices = PriceSnapshot.objects.count()
prices_24h   = PriceSnapshot.objects.filter(timestamp__gte=timezone.now()-timedelta(hours=24)).count()
last_price   = PriceSnapshot.objects.order_by("-timestamp").first()
print(f"\n=== PRICE SNAPSHOTS ===")
print(f"  Total:       {total_prices}")
print(f"  Last 24h:    {prices_24h}")
if last_price:
    age = timezone.now() - last_price.timestamp
    print(f"  Most recent: {last_price.timestamp}  ticker={last_price.ticker.symbol}  price={last_price.price}  age={int(age.total_seconds()//60)}m")
else:
    print("  No price data in DB")

# --- Per-ticker signal summary ---
print(f"\n=== LATEST SIGNAL PER TICKER ===")
for t in tickers:
    sig = SignalSnapshot.objects.filter(ticker__symbol=t["symbol"]).order_by("-created_at").first()
    if sig:
        age = timezone.now() - sig.created_at
        hrs = int(age.total_seconds() // 3600)
        mins = int((age.total_seconds() % 3600) // 60)
        print(f"  {t['symbol']:6} {sig.signal:4}  sent={sig.sentiment:.2f}  mom={sig.momentum:.2f}  cons={sig.consistency:.2f}  posts={sig.post_count:3}  age={hrs}h{mins}m")
    else:
        print(f"  {t['symbol']:6} NO SIGNAL")
