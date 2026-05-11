import logging
import time
from datetime import datetime
from datetime import timezone as dt_timezone

import requests
from decouple import config

from .base import BaseFetcher

logger = logging.getLogger(__name__)

SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "StockMarket",
    "options",
    "SecurityAnalysis",
    "algotrading",
    "dividends",
]
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
SEARCH_URL = "https://oauth.reddit.com/r/{subreddit}/search.json"
PUBLIC_SEARCH_URL = "https://www.reddit.com/r/{subreddit}/search.json"
PUBLIC_SUBREDDITS = [
    "wallstreetbets",
    "stocks",
    "investing",
    "StockMarket",
]
PUBLIC_REQUEST_DELAY_SECONDS = 2.0


class RedditFetcher(BaseFetcher):
    source = "reddit"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        user_agent: str | None = None,
        *,
        limit: int = 100,
        max_pages: int = 1,
        allow_public_fallback: bool = True,
        public_delay_seconds: float = PUBLIC_REQUEST_DELAY_SECONDS,
    ):
        self.client_id = client_id if client_id is not None else config("REDDIT_CLIENT_ID", default="")
        self.client_secret = (
            client_secret if client_secret is not None else config("REDDIT_CLIENT_SECRET", default="")
        )
        self.user_agent = user_agent if user_agent is not None else config("REDDIT_USER_AGENT", default="")
        self.limit = min(max(limit, 1), 100)
        self.max_pages = max(max_pages, 1)
        self.allow_public_fallback = allow_public_fallback
        self.public_delay_seconds = max(public_delay_seconds, 0)
        self._access_token: str | None = None

    def fetch(self, symbol: str) -> list[dict]:
        token = self._get_access_token()
        if not token:
            if self.allow_public_fallback and self.user_agent:
                logger.warning("Reddit OAuth unavailable for %s; using public JSON fallback", symbol)
                return self._fetch_public_json(symbol)
            logger.warning("Reddit fetch skipped for %s: missing or invalid OAuth credentials", symbol)
            return []

        posts = []
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": self.user_agent,
        }
        for subreddit in SUBREDDITS:
            after = None
            for _page in range(self.max_pages):
                data = self.request_json(
                    "GET",
                    SEARCH_URL.format(subreddit=subreddit),
                    headers=headers,
                    params={
                        "q": symbol,
                        "restrict_sr": "true",
                        "sort": "new",
                        "limit": self.limit,
                        **({"after": after} if after else {}),
                    },
                )
                if not data:
                    break

                listing = data.get("data", {})
                children = listing.get("children", [])
                for child in children:
                    parsed = self._parse_listing_child(child)
                    if parsed:
                        posts.append(parsed)

                after = listing.get("after")
                if not after:
                    break

        return posts

    def _fetch_public_json(self, symbol: str) -> list[dict]:
        posts = []
        headers = {"User-Agent": self.user_agent}
        # Public JSON is deliberately conservative: one page across fewer subreddits.
        for index, subreddit in enumerate(PUBLIC_SUBREDDITS):
            if index > 0 and self.public_delay_seconds:
                time.sleep(self.public_delay_seconds)

            data = self.request_json(
                "GET",
                PUBLIC_SEARCH_URL.format(subreddit=subreddit),
                retries=0,
                headers=headers,
                params={
                    "q": symbol,
                    "restrict_sr": "true",
                    "sort": "new",
                    "limit": min(self.limit, 25),
                    "raw_json": 1,
                },
            )
            if not data:
                continue

            listing = data.get("data", {})
            children = listing.get("children", [])
            for child in children:
                parsed = self._parse_listing_child(child, fetch_mode="public_json")
                if parsed:
                    posts.append(parsed)

        return posts

    def _get_access_token(self) -> str | None:
        if self._access_token:
            return self._access_token
        if not self.client_id or not self.client_secret or not self.user_agent:
            return None

        try:
            response = requests.post(
                TOKEN_URL,
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
            response.raise_for_status()
            token = response.json().get("access_token")
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Reddit OAuth token request failed: %s", exc)
            return None

        if not token:
            logger.warning("Reddit OAuth token response did not include access_token")
            return None

        self._access_token = token
        return token

    def _parse_listing_child(self, child: dict, *, fetch_mode: str = "oauth") -> dict | None:
        data = child.get("data") if isinstance(child, dict) else None
        if not isinstance(data, dict):
            return None

        external_id = data.get("name") or data.get("id")
        if not external_id:
            return None

        title = data.get("title") or ""
        permalink = data.get("permalink") or ""
        post_url = data.get("url") or (f"https://www.reddit.com{permalink}" if permalink else "")
        body = data.get("selftext") or data.get("selftext_html") or ""

        return {
            "source": "reddit",
            "external_id": str(external_id),
            "title": title,
            "url": post_url,
            "content": body or title,
            "posted_at": self._parse_date(data.get("created_utc")),
            "metadata": {
                "score": data.get("score"),
                "comments_count": data.get("num_comments"),
                "subreddit": data.get("subreddit"),
                "fetch_mode": fetch_mode,
            },
        }

    def _parse_date(self, timestamp: int | float | str | None) -> datetime:
        if timestamp is None:
            return datetime.now(tz=dt_timezone.utc)
        try:
            return datetime.fromtimestamp(float(timestamp), tz=dt_timezone.utc)
        except (TypeError, ValueError, OSError):
            return datetime.now(tz=dt_timezone.utc)
