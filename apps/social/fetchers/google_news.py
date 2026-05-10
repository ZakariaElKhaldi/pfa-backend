import logging
import re
from datetime import datetime
from datetime import timezone as dt_timezone
from email.utils import parsedate
from urllib.parse import quote_plus

import feedparser

from .base import BaseFetcher

logger = logging.getLogger(__name__)

# Google News RSS (search for ticker)
GOOGLE_RSS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

COMPANY_SUFFIXES = {
    "class",
    "co",
    "company",
    "corp",
    "corporation",
    "group",
    "holdings",
    "inc",
    "incorporated",
    "ltd",
    "plc",
}


def company_keywords(company_name: str | None) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9]+", company_name or "")
    return {
        word.lower()
        for word in words
        if len(word) >= 4 and word.lower() not in COMPANY_SUFFIXES
    }


def is_relevant_google_post(
    symbol: str,
    company_name: str | None,
    title: str | None,
    content: str | None,
) -> bool:
    text = f"{title or ''} {content or ''}".lower()
    normalized_symbol = symbol.upper()
    symbol_pattern = re.compile(rf"(?<![A-Za-z0-9])\$?{re.escape(normalized_symbol)}(?![A-Za-z0-9])", re.I)
    symbol_matches = bool(symbol_pattern.search(text))
    company_matches = any(keyword in text for keyword in company_keywords(company_name))

    if len(normalized_symbol) <= 3 and company_name:
        return company_matches
    return symbol_matches or company_matches


def build_google_news_query(symbol: str, company_name: str | None = None) -> str:
    if company_name:
        return quote_plus(f'"{symbol}" "{company_name}" stock')
    return quote_plus(f'"{symbol}" stock')


class GoogleNewsFetcher(BaseFetcher):
    def fetch(self, symbol: str, company_name: str | None = None) -> list[dict]:
        url = GOOGLE_RSS_URL.format(query=build_google_news_query(symbol, company_name))
        try:
            feed = feedparser.parse(url)
            posts = []
            for entry in feed.entries:
                title = entry.get("title", "")
                content = entry.get("summary", "")
                if not is_relevant_google_post(symbol, company_name, title, content):
                    continue
                posts.append({
                    "source": "news_google",
                    "external_id": entry.get("id", entry.get("link", "")),
                    "title": title,
                    "url": entry.get("link", ""),
                    "content": content,
                    "posted_at": self._parse_date(entry.get("published"))
                })
            return posts
        except Exception as e:
            logger.error("Google News fetch failed for %s: %s", symbol, e)
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
