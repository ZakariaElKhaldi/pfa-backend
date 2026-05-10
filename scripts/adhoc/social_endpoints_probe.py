#!/usr/bin/env python3
"""Probe social endpoints and print compact reproducible diagnostics.

Examples:
  python scripts/adhoc/social_endpoints_probe.py --base-url http://127.0.0.1:8000 --symbol XOM
  python scripts/adhoc/social_endpoints_probe.py --base-url http://127.0.0.1:8000 --symbol XOM --token "$TOKEN"
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENDPOINTS = [
    ("social_feed_global", "/api/social/feed/", {}),
    ("social_feed_symbol", "/api/social/feed/", {"symbol": "{symbol}"}),
    ("social_trending", "/api/social/trending/", {}),
    ("ticker_posts", "/api/tickers/{symbol}/posts/", {}),
    ("ticker_sentiment", "/api/tickers/{symbol}/social/sentiment/", {}),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--symbol", default="XOM")
    parser.add_argument("--token", default="")
    parser.add_argument("--top", type=int, default=10, help="number of ids/timestamps rows to print")
    return parser.parse_args()


def fetch_json(url: str, token: str) -> tuple[int, Any]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url=url, headers=headers, method="GET")

    try:
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(body) if body else {"error": exc.reason}
        except json.JSONDecodeError:
            parsed = {"error": body or str(exc.reason)}
        return exc.code, parsed
    except URLError as exc:
        return 0, {"error": str(exc.reason)}


def summarize_rows(name: str, rows: list[dict[str, Any]], top: int) -> None:
    source_counts = Counter(str(row.get("source") or "" ) for row in rows if isinstance(row, dict))
    ticker_counts = Counter(str(row.get("ticker") or "" ) for row in rows if isinstance(row, dict))

    print(f"  rows={len(rows)}")
    if source_counts:
        print("  source_mix=" + ", ".join(f"{k}:{v}" for k, v in source_counts.most_common()))
    if ticker_counts:
        print("  ticker_mix_by_id=" + ", ".join(f"{k}:{v}" for k, v in ticker_counts.most_common()))

    sample = rows[:top]
    if not sample:
        return
    print("  top_rows=")
    for row in sample:
        row_id = row.get("id")
        posted_at = row.get("posted_at")
        source = row.get("source")
        external_id = row.get("external_id")
        print(f"    id={row_id} posted_at={posted_at} source={source} external_id={external_id}")

    google = [r for r in rows if r.get("source") == "news_google"]
    if google:
        g = google[0]
        title = str(g.get("title") or "")
        content = str(g.get("content") or "")
        display = str(g.get("display_content") or "")
        print("  sample_google=")
        print(f"    title={title[:120]}")
        print(f"    content={content[:120]}")
        print(f"    display_content={display[:120]}")


def main() -> int:
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    for name, path_tmpl, query_tmpl in ENDPOINTS:
        path = path_tmpl.format(symbol=args.symbol)
        query = {
            k: v.format(symbol=args.symbol)
            for k, v in query_tmpl.items()
        }
        url = f"{base_url}{path}"
        if query:
            url += "?" + urlencode(query)

        status, payload = fetch_json(url, token=args.token)
        print(f"[{name}] {url}")
        print(f"  status={status}")

        if isinstance(payload, list):
            summarize_rows(name, payload, args.top)
        elif isinstance(payload, dict):
            print("  body=" + json.dumps(payload, sort_keys=True))
        else:
            print(f"  body_type={type(payload).__name__}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
