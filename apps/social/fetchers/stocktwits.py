import logging
from datetime import datetime
from datetime import timezone as dt_timezone

from .base import BaseFetcher

logger = logging.getLogger(__name__)

ST_URL = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"


class StockTwitsFetcher(BaseFetcher):
    source = "stocktwits"

    def fetch(self, symbol: str) -> list[dict]:
        url = ST_URL.format(symbol=symbol)
        data = self.request_json("GET", url)
        if not data:
            return []

        posts = []
        for msg in data.get("messages", []):
            external_id = msg.get("id")
            if external_id is None:
                continue

            entities = msg.get("entities") or {}
            sentiment = entities.get("sentiment") or {}
            label = sentiment.get("basic")
            body = msg.get("body", "")
            posts.append(
                {
                    "source": "stocktwits",
                    "external_id": str(external_id),
                    "title": "",
                    "url": self._message_url(msg),
                    "content": body,
                    "posted_at": self._parse_date(msg.get("created_at")),
                    "metadata": {
                        "sentiment": label.lower() if isinstance(label, str) else None,
                    },
                }
            )
        return posts

    def _message_url(self, msg: dict) -> str:
        user = msg.get("user") or {}
        username = user.get("username")
        message_id = msg.get("id")
        if username and message_id:
            return f"https://stocktwits.com/{username}/message/{message_id}"
        return ""

    def _parse_date(self, date_str: str | None) -> datetime:
        if not date_str:
            return datetime.now(tz=dt_timezone.utc)
        try:
            return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt_timezone.utc)
        except Exception:
            return datetime.now(tz=dt_timezone.utc)
