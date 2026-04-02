import logging
from datetime import datetime, timezone as dt_timezone
from email.utils import parsedate

import feedparser

from .base import BaseFetcher

logger = logging.getLogger(__name__)

SUBREDDITS = ["wallstreetbets", "stocks", "investing", "StockMarket"]
RSS_URL = "https://www.reddit.com/r/{subreddit}/search.rss?q={symbol}&sort=new&restrict_sr=1"


class RedditFetcher(BaseFetcher):
    def fetch(self, symbol: str) -> list[dict]:
        posts = []
        for subreddit in SUBREDDITS:
            url = RSS_URL.format(subreddit=subreddit, symbol=symbol)
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    posts.append(
                        {
                            "source": "reddit",
                            "external_id": entry.get("id", ""),
                            "content": f"{entry.get('title', '')} {entry.get('summary', '')}".strip(),
                            "posted_at": self._parse_date(entry.get("published")),
                        }
                    )
            except Exception as e:
                logger.error("Reddit fetch failed for %s/%s: %s", subreddit, symbol, e)
        return posts

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
