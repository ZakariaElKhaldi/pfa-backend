import pytest
from unittest.mock import patch, MagicMock
from apps.sentiment.scorer import SentimentScorer


def make_mock_pipeline(positive=0.7, negative=0.1, neutral=0.2):
    mock_result = [
        [
            {"label": "Positive", "score": positive},
            {"label": "Negative", "score": negative},
            {"label": "Neutral", "score": neutral},
        ]
    ]
    mock_pipe = MagicMock(return_value=mock_result)
    return mock_pipe


@patch("apps.sentiment.scorer.pipeline")
def test_bullish_score(mock_pipeline_fn):
    mock_pipeline_fn.return_value = make_mock_pipeline(positive=0.8, negative=0.05)
    scorer = SentimentScorer()
    scorer._pipeline = None  # force reload with mock

    with patch.object(scorer, "_load"):
        scorer._pipeline = make_mock_pipeline(positive=0.8, negative=0.05)
        score, label = scorer.score("AAPL is absolutely crushing it this quarter")
        assert score == pytest.approx(0.75, abs=0.01)
        assert label == "bullish"


@patch("apps.sentiment.scorer.pipeline")
def test_bearish_score(mock_pipeline_fn):
    scorer = SentimentScorer()
    scorer._pipeline = make_mock_pipeline(positive=0.05, negative=0.85)
    with patch.object(scorer, "_load"):
        score, label = scorer.score("This stock is going to crash hard")
        assert score == pytest.approx(-0.80, abs=0.01)
        assert label == "bearish"


@patch("apps.sentiment.scorer.pipeline")
def test_neutral_score(mock_pipeline_fn):
    scorer = SentimentScorer()
    scorer._pipeline = make_mock_pipeline(positive=0.35, negative=0.35, neutral=0.30)
    with patch.object(scorer, "_load"):
        score, label = scorer.score("AAPL trading sideways today")
        assert abs(score) <= 0.1
        assert label == "neutral"


def test_text_truncated_at_512_chars():
    scorer = SentimentScorer()
    long_text = "x" * 1000
    mock_pipe = make_mock_pipeline()
    scorer._pipeline = mock_pipe
    with patch.object(scorer, "_load"):
        scorer.score(long_text)
        called_text = mock_pipe.call_args[0][0]
        assert len(called_text) <= 512
