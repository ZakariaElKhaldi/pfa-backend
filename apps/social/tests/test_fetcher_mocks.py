import pytest
from unittest.mock import MagicMock, patch
from apps.social.fetchers.reddit import RedditFetcher
from apps.social.fetchers.stocktwits import StockTwitsFetcher

class TestFetcherMocks:
    @patch("feedparser.parse")
    def test_reddit_fetcher(self, mock_parse):
        # Mock feedparser response
        mock_feed = MagicMock()
        mock_feed.entries = [
            {
                "id": "post1",
                "title": "NVIDIA is mooning",
                "summary": "Check out NVDA financial results.",
                "published": "Wed, 02 Apr 2026 20:00:00 GMT"
            }
        ]
        mock_parse.return_value = mock_feed
        
        fetcher = RedditFetcher()
        posts = fetcher.fetch("NVDA")
        
        # RedditFetcher iterates over 4 subreddits, so it should call parse 4 times
        assert mock_parse.call_count == 4
        # Since we used the same mock for all, we expect 4 * 1 posts
        assert len(posts) == 4
        assert posts[0]["source"] == "reddit"
        assert posts[0]["title"] == "NVIDIA is mooning"
        assert "NVDA financial results" in posts[0]["content"]

    @patch("requests.get")
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

    @patch("requests.get")
    def test_stocktwits_error_handling(self, mock_get):
        mock_get.side_effect = Exception("API Down")
        
        fetcher = StockTwitsFetcher()
        posts = fetcher.fetch("NVDA")
        
        assert posts == []
