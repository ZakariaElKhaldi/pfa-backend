import logging
from datetime import datetime, timezone as dt_timezone

import requests

from .base import BaseFetcher

logger = logging.getLogger(__name__)

ST_URL = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"


class StockTwitsFetcher(BaseFetcher):
    def fetch(self, symbol: str) -> list[dict]:
        url = ST_URL.format(symbol=symbol)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            posts = []
            for msg in data.get("messages", []):
                posts.append(
                    {
                        "source": "stocktwits",
                        "external_id": str(msg["id"]),
                        "content": msg.get("body", ""),
                        "posted_at": self._parse_date(msg.get("created_at")),
                    }
                )
            return posts
        except Exception as e:
            logger.error("StockTwits fetch failed for %s: %s", symbol, e)
            return []

    def _parse_date(self, date_str: str | None) -> datetime:
        if not date_str:
            return datetime.now(tz=dt_timezone.utc)
        try:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=dt_timezone.utc
            )
        except Exception:
            return datetime.now(tz=dt_timezone.utc)
