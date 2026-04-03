from unittest.mock import MagicMock, patch

from apps.social.fetchers.reddit import RedditFetcher
from apps.social.fetchers.stocktwits import StockTwitsFetcher

FAKE_FEED = MagicMock()
FAKE_FEED.entries = [
    MagicMock(
        id="t3_abc123",
        title="AAPL is looking bullish today",
        summary="Strong earnings expected next quarter",
        published="Mon, 01 Apr 2026 10:00:00 +0000",
    ),
    MagicMock(
        id="t3_def456",
        title="Short post",
        summary="",
        published="Mon, 01 Apr 2026 11:00:00 +0000",
    ),
]


@patch("apps.social.fetchers.reddit.feedparser.parse", return_value=FAKE_FEED)
def test_reddit_fetcher_returns_posts(mock_parse):
    fetcher = RedditFetcher()
    posts = fetcher.fetch("AAPL")
    # 4 subreddits * 2 entries = 8
    assert len(posts) == 8
    assert all(p["source"] == "reddit" for p in posts)
    assert all("external_id" in p for p in posts)
    assert all("content" in p for p in posts)
    assert all("posted_at" in p for p in posts)


@patch("apps.social.fetchers.reddit.feedparser.parse", side_effect=Exception("network error"))
def test_reddit_fetcher_skips_on_error(mock_parse):
    fetcher = RedditFetcher()
    posts = fetcher.fetch("AAPL")
    assert posts == []


# STOCKTWITS TESTS
FAKE_ST_RESPONSE = {
    "messages": [
        {
            "id": 111111,
            "body": "TSLA to the moon! Strong buy signal.",
            "created_at": "2026-04-01T10:00:00Z",
        },
        {
            "id": 222222,
            "body": "Bearish on TSLA short term.",
            "created_at": "2026-04-01T11:00:00Z",
        },
    ]
}


@patch("apps.social.fetchers.stocktwits.requests.get")
def test_stocktwits_fetcher_returns_posts(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = lambda: None
    mock_get.return_value.json.return_value = FAKE_ST_RESPONSE

    fetcher = StockTwitsFetcher()
    posts = fetcher.fetch("TSLA")
    assert len(posts) == 2
    assert all(p["source"] == "stocktwits" for p in posts)
    assert posts[0]["external_id"] == "111111"
    assert "moon" in posts[0]["content"]


@patch("apps.social.fetchers.stocktwits.requests.get", side_effect=Exception("timeout"))
def test_stocktwits_fetcher_skips_on_error(mock_get):
    fetcher = StockTwitsFetcher()
    posts = fetcher.fetch("TSLA")
    assert posts == []
