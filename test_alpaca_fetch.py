from apps.social.fetchers.alpaca_news import AlpacaNewsFetcher
from alpaca.data.requests import NewsRequest

fetcher = AlpacaNewsFetcher()
request_params = NewsRequest(symbols="MSFT", limit=2)
news = fetcher.client.get_news(request_params)

print("Keys in news.data:", list(news.data.keys()))
for k, v in news.data.items():
    print(f"Type of news.data['{k}']: {type(v)}")
    if isinstance(v, list) and len(v) > 0:
        print(f"First item type: {type(v[0])}")
        print(f"First item dir: {dir(v[0])}")
        print(f"First item: {v[0]}")
