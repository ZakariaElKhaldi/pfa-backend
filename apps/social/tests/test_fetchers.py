from unittest.mock import MagicMock, patch

import requests

from apps.social.fetchers.google_news import GoogleNewsFetcher, is_relevant_google_post
from apps.social.fetchers.reddit import RedditFetcher
from apps.social.fetchers.stocktwits import StockTwitsFetcher

FAKE_REDDIT_RESPONSE = {
    "data": {
        "after": None,
        "children": [
            {
                "data": {
                    "name": "t3_abc123",
                    "title": "AAPL is looking bullish today",
                    "selftext": "Strong earnings expected next quarter",
                    "url": "https://reddit.com/r/stocks/comments/abc123",
                    "created_utc": 1775037600,
                    "score": 42,
                    "num_comments": 7,
                    "subreddit": "stocks",
                }
            },
            {
                "data": {
                    "name": "t3_def456",
                    "title": "AAPL earnings thread",
                    "selftext": "",
                    "permalink": "/r/investing/comments/def456/aapl/",
                    "created_utc": 1775041200,
                }
            },
        ],
    }
}


@patch("apps.social.fetchers.reddit.requests.post")
@patch("apps.social.fetchers.base.requests.request")
def test_reddit_fetcher_returns_posts(mock_request, mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = lambda: None
    mock_post.return_value.json.return_value = {"access_token": "token"}
    mock_request.return_value.status_code = 200
    mock_request.return_value.raise_for_status = lambda: None
    mock_request.return_value.json.return_value = FAKE_REDDIT_RESPONSE

    fetcher = RedditFetcher("client", "secret", "crowdsignal-test/1.0")
    posts = fetcher.fetch("AAPL")

    assert len(posts) == 16
    assert all(p["source"] == "reddit" for p in posts)
    assert all("external_id" in p for p in posts)
    assert all("content" in p for p in posts)
    assert all("posted_at" in p for p in posts)
    assert posts[0]["metadata"]["score"] == 42
    assert mock_request.call_args.kwargs["headers"]["User-Agent"] == "crowdsignal-test/1.0"


@patch("apps.social.fetchers.reddit.requests.post", side_effect=requests.Timeout("network error"))
def test_reddit_fetcher_skips_on_oauth_error(mock_post):
    fetcher = RedditFetcher("client", "secret", "crowdsignal-test/1.0")
    posts = fetcher.fetch("AAPL")
    assert posts == []


def test_reddit_fetcher_skips_without_credentials():
    fetcher = RedditFetcher("", "", "")
    posts = fetcher.fetch("AAPL")
    assert posts == []


@patch("apps.social.fetchers.reddit.SUBREDDITS", ["stocks"])
@patch("apps.social.fetchers.reddit.requests.post")
@patch("apps.social.fetchers.base.requests.request")
def test_reddit_fetcher_follows_listing_pagination(mock_request, mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = lambda: None
    mock_post.return_value.json.return_value = {"access_token": "token"}
    mock_request.return_value.status_code = 200
    mock_request.return_value.raise_for_status = lambda: None
    mock_request.return_value.json.side_effect = [
        {
            "data": {
                "after": "page2",
                "children": [
                    {
                        "data": {
                            "name": "t3_page1",
                            "title": "AAPL page one",
                            "selftext": "Apple demand is strong",
                            "created_utc": 1775037600,
                        }
                    }
                ],
            }
        },
        {
            "data": {
                "after": None,
                "children": [
                    {
                        "data": {
                            "name": "t3_page2",
                            "title": "AAPL page two",
                            "selftext": "Apple services growth remains durable",
                            "created_utc": 1775041200,
                        }
                    }
                ],
            }
        },
    ]

    posts = RedditFetcher("client", "secret", "crowdsignal-test/1.0", max_pages=2).fetch("AAPL")

    assert [post["external_id"] for post in posts] == ["t3_page1", "t3_page2"]
    assert mock_request.call_args_list[1].kwargs["params"]["after"] == "page2"


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


@patch("apps.social.fetchers.base.requests.request")
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


@patch("apps.social.fetchers.base.requests.request", side_effect=requests.Timeout("timeout"))
def test_stocktwits_fetcher_skips_on_error(mock_get):
    fetcher = StockTwitsFetcher()
    posts = fetcher.fetch("TSLA")
    assert posts == []


@patch("apps.social.fetchers.base.time.sleep", return_value=None)
@patch("apps.social.fetchers.base.requests.request")
def test_stocktwits_fetcher_skips_on_429(mock_get, mock_sleep):
    mock_get.return_value.status_code = 429
    mock_get.return_value.headers = {"Retry-After": "0"}

    posts = StockTwitsFetcher().fetch("TSLA")

    assert posts == []


@patch("apps.social.fetchers.base.requests.request")
def test_stocktwits_fetcher_skips_malformed_json(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = lambda: None
    mock_get.return_value.json.side_effect = ValueError("bad json")

    posts = StockTwitsFetcher().fetch("TSLA")

    assert posts == []


def test_google_relevance_rejects_ambiguous_symbol_without_company_match():
    assert not is_relevant_google_post(
        "V",
        "Visa Inc.",
        "Real Madrid v FC Barcelona live stream",
        "Watch the match online.",
    )
    assert is_relevant_google_post(
        "V",
        "Visa Inc.",
        "Visa shares rise after earnings",
        "Card spending increased.",
    )


@patch("apps.social.fetchers.google_news.feedparser.parse")
def test_google_fetcher_uses_company_query_and_filters_irrelevant_results(mock_parse):
    mock_feed = MagicMock()
    mock_feed.entries = [
        {
            "id": "bad",
            "title": "Real Madrid v FC Barcelona live stream",
            "summary": "Sports stream listing.",
            "published": "Mon, 01 Apr 2026 10:00:00 +0000",
        },
        {
            "id": "good",
            "title": "Visa shares rise after earnings",
            "summary": "Visa revenue increased.",
            "published": "Mon, 01 Apr 2026 11:00:00 +0000",
        },
    ]
    mock_parse.return_value = mock_feed

    posts = GoogleNewsFetcher().fetch("V", "Visa Inc.")

    assert [post["external_id"] for post in posts] == ["good"]
    assert "%22V%22+%22Visa+Inc.%22+stock" in mock_parse.call_args.args[0]
