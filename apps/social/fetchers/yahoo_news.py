import logging
from datetime import datetime
from datetime import timezone as dt_timezone
from email.utils import parsedate

import feedparser

from .base import BaseFetcher

logger = logging.getLogger(__name__)

# Yahoo Finance News RSS
YAHOO_RSS_URL = "https://finance.yahoo.com/rss/headline?s={symbol}"


class YahooNewsFetcher(BaseFetcher):
    def fetch(self, symbol: str) -> list[dict]:
        url = YAHOO_RSS_URL.format(symbol=symbol)
        try:
            feed = feedparser.parse(url)
            posts = []
            for entry in feed.entries:
                posts.append({
                    "source": "news_yahoo",
                    "external_id": entry.get("id", entry.get("link", "")),
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "content": entry.get("summary", ""),
                    "posted_at": self._parse_date(entry.get("published"))
                })
            return posts
        except Exception as e:
            logger.error("Yahoo News fetch failed for %s: %s", symbol, e)
            return []

    def _parse_date(self, date_str: str | None) -> datetime:
        if not date_str:
            return datetime.now(tz=dt_timezone.utc)
        try:
            parsed = parsedate(date_str)
            if parsed:
                return datetime(*parsed[:6], tzinfo=dt_timezone.utc)
        except Exception:
            pass
        return datetime.now(tz=dt_timezone.utc)
