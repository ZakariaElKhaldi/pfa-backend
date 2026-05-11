import pytest
import requests
from unittest.mock import MagicMock, patch
from apps.social.fetchers.reddit import RedditFetcher
from apps.social.fetchers.stocktwits import StockTwitsFetcher

class TestFetcherMocks:
    @patch("apps.social.fetchers.reddit.requests.post")
    @patch("apps.social.fetchers.base.requests.request")
    def test_reddit_fetcher(self, mock_request, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = {"access_token": "token"}
        mock_request.return_value.status_code = 200
        mock_request.return_value.raise_for_status = lambda: None
        mock_request.return_value.json.return_value = {
            "data": {
                "after": None,
                "children": [
                    {
                        "data": {
                            "name": "post1",
                            "title": "NVIDIA is mooning",
                            "selftext": "Check out NVDA financial results.",
                            "url": "https://reddit.com/r/stocks/comments/post1",
                            "created_utc": 1775160000,
                        }
                    }
                ],
            }
        }

        fetcher = RedditFetcher("client", "secret", "crowdsignal-test/1.0")
        posts = fetcher.fetch("NVDA")

        assert mock_request.call_count == 8
        assert len(posts) == 8
        assert posts[0]["metadata"]["fetch_mode"] == "oauth"
        assert posts[0]["source"] == "reddit"
        assert posts[0]["title"] == "NVIDIA is mooning"
        assert "NVDA financial results" in posts[0]["content"]

    @patch("apps.social.fetchers.base.requests.request")
    def test_stocktwits_fetcher(self, mock_get):
        # Mock requests response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "messages": [
                {
                    "id": 12345,
                    "body": "$NVDA looking bullish!",
                    "created_at": "2026-04-02T21:00:00Z"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        fetcher = StockTwitsFetcher()
        posts = fetcher.fetch("NVDA")
        
        assert len(posts) == 1
        assert posts[0]["source"] == "stocktwits"
        assert posts[0]["content"] == "$NVDA looking bullish!"
        assert posts[0]["external_id"] == "12345"

    @patch("apps.social.fetchers.base.requests.request")
    def test_stocktwits_error_handling(self, mock_get):
        mock_get.side_effect = requests.RequestException("API Down")
        
        fetcher = StockTwitsFetcher()
        posts = fetcher.fetch("NVDA")
        
        assert posts == []
