import logging
from datetime import datetime
from decouple import config

from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest

from .base import BaseFetcher

logger = logging.getLogger(__name__)


class AlpacaNewsFetcher(BaseFetcher):
    def __init__(self):
        self.api_key = config("ALPACA_API_KEY", default="")
        self.secret_key = config("ALPACA_SECRET_KEY", default="")
        try:
            self.client = NewsClient(self.api_key, self.secret_key)
        except Exception as e:
            logger.error("Failed to initialize Alpaca NewsClient: %s", e)
            self.client = None

    def fetch(self, symbol: str) -> list[dict]:
        if not self.client:
            return []

        try:
            # Alpaca SDK NewsRequest in some versions expects symbols as a string or list
            request_params = NewsRequest(
                symbols=symbol,
                limit=10
            )
            news = self.client.get_news(request_params)
            
            posts = []
            for item in news.news:
                posts.append({
                    "source": "news_alpaca",
                    "external_id": str(item.id),
                    "title": item.headline,
                    "url": item.url,
                    "content": item.summary,
                    "posted_at": item.created_at
                })
            return posts
        except Exception as e:
            logger.error("Alpaca News fetch failed for %s: %s", symbol, e)
            return []
