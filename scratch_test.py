from apps.tickers.models import Ticker
from apps.pipeline.pipeline import run_pipeline_for_ticker
from apps.social.models import SocialPost
from apps.signals.models import SignalSnapshot

print("\n--- 1. Setting up Ticker ---")
ticker, created = Ticker.objects.get_or_create(symbol='MSFT', defaults={'name': 'Microsoft'})
if created:
    print(f"Created new ticker: {ticker.symbol}")
else:
    print(f"Using existing ticker: {ticker.symbol}")

print("\n--- 2. Running Pipeline (Scraping & Cleaning) ---")
run_pipeline_for_ticker(ticker.symbol)
print("Pipeline execution completed.")

print("\n--- 3. Verifying Scraped Posts ---")
posts = SocialPost.objects.filter(ticker=ticker).order_by('-posted_at')
print(f"Total posts collected: {posts.count()}")
if posts.exists():
    latest_post = posts.first()
    print(f"Sample Latest Post:\n  Source: {latest_post.source}\n  Content: {latest_post.content[:150]}...\n  Cleaned Text Length: {len(latest_post.cleaned_text)}\n  Sentiment Score: {latest_post.sentiment_score}")

print("\n--- 4. Verifying Generated Signal ---")
signals = SignalSnapshot.objects.filter(ticker=ticker).order_by('-created_at')
print(f"Total signals generated: {signals.count()}")
if signals.exists():
    latest_signal = signals.first()
    print(f"Latest Signal Result:\n  Action: {latest_signal.action}\n  Bullish Score: {latest_signal.bullish_score}\n  Bearish Score: {latest_signal.bearish_score}\n  Explanation: {latest_signal.explanation}")
