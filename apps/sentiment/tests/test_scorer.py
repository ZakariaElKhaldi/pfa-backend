from unittest.mock import MagicMock, patch

import pytest

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


# --- Phase 1.2: score_detail and batch scoring tests ---


def test_score_detail_returns_all_three_probabilities():
    scorer = SentimentScorer()
    scorer._pipeline = make_mock_pipeline(positive=0.7, negative=0.1, neutral=0.2)
    with patch.object(scorer, "_load"):
        detail = scorer.score_detail("AAPL is great")
        assert "positive_prob" in detail
        assert "negative_prob" in detail
        assert "neutral_prob" in detail
        assert detail["positive_prob"] == pytest.approx(0.7)
        assert detail["negative_prob"] == pytest.approx(0.1)
        assert detail["neutral_prob"] == pytest.approx(0.2)


def test_score_detail_probabilities_sum_to_approximately_one():
    scorer = SentimentScorer()
    scorer._pipeline = make_mock_pipeline(positive=0.6, negative=0.25, neutral=0.15)
    with patch.object(scorer, "_load"):
        detail = scorer.score_detail("test text")
        total = detail["positive_prob"] + detail["negative_prob"] + detail["neutral_prob"]
        assert total == pytest.approx(1.0, abs=0.01)


def test_score_detail_includes_composite_score_and_label():
    scorer = SentimentScorer()
    scorer._pipeline = make_mock_pipeline(positive=0.8, negative=0.05, neutral=0.15)
    with patch.object(scorer, "_load"):
        detail = scorer.score_detail("bullish text")
        assert "composite_score" in detail
        assert "label" in detail
        assert detail["composite_score"] == pytest.approx(0.75, abs=0.01)
        assert detail["label"] == "bullish"


def test_score_detail_bearish():
    scorer = SentimentScorer()
    scorer._pipeline = make_mock_pipeline(positive=0.05, negative=0.85, neutral=0.10)
    with patch.object(scorer, "_load"):
        detail = scorer.score_detail("crash coming")
        assert detail["label"] == "bearish"
        assert detail["composite_score"] == pytest.approx(-0.80, abs=0.01)


def test_score_detail_neutral():
    scorer = SentimentScorer()
    scorer._pipeline = make_mock_pipeline(positive=0.35, negative=0.35, neutral=0.30)
    with patch.object(scorer, "_load"):
        detail = scorer.score_detail("sideways trading")
        assert detail["label"] == "neutral"
        assert abs(detail["composite_score"]) <= 0.1


def make_mock_batch_pipeline(results_list):
    """Create a mock pipeline that handles batch input (list of texts)."""
    mock_pipe = MagicMock(side_effect=lambda texts: [
        [
            {"label": "Positive", "score": r[0]},
            {"label": "Negative", "score": r[1]},
            {"label": "Neutral", "score": r[2]},
        ]
        for r in results_list
    ] if isinstance(texts, list) else [
        [
            {"label": "Positive", "score": results_list[0][0]},
            {"label": "Negative", "score": results_list[0][1]},
            {"label": "Neutral", "score": results_list[0][2]},
        ]
    ])
    return mock_pipe


def test_score_batch_returns_list_of_detail_dicts():
    scorer = SentimentScorer()
    results = [(0.8, 0.1, 0.1), (0.1, 0.7, 0.2)]
    scorer._pipeline = make_mock_batch_pipeline(results)
    with patch.object(scorer, "_load"):
        batch_results = scorer.score_batch(["bullish text", "bearish text"])
        assert len(batch_results) == 2
        assert batch_results[0]["positive_prob"] == pytest.approx(0.8)
        assert batch_results[0]["label"] == "bullish"
        assert batch_results[1]["negative_prob"] == pytest.approx(0.7)
        assert batch_results[1]["label"] == "bearish"


def test_score_batch_calls_pipeline_once_not_per_text():
    scorer = SentimentScorer()
    results = [(0.5, 0.3, 0.2), (0.3, 0.5, 0.2), (0.3, 0.3, 0.4)]
    scorer._pipeline = make_mock_batch_pipeline(results)
    with patch.object(scorer, "_load"):
        scorer.score_batch(["text1", "text2", "text3"])
        # Pipeline should be called once with all texts, not 3 times
        assert scorer._pipeline.call_count == 1


def test_score_batch_empty_list():
    scorer = SentimentScorer()
    scorer._pipeline = MagicMock()
    with patch.object(scorer, "_load"):
        result = scorer.score_batch([])
        assert result == []


def test_score_backward_compatible_returns_tuple():
    """Existing score() must still return (float, str) tuple."""
    scorer = SentimentScorer()
    scorer._pipeline = make_mock_pipeline(positive=0.7, negative=0.1, neutral=0.2)
    with patch.object(scorer, "_load"):
        result = scorer.score("test")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], str)
