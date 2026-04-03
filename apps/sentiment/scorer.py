import logging

from transformers import pipeline

logger = logging.getLogger(__name__)


class SentimentScorer:
    """Singleton FinBERT scorer. Call score(), score_detail(), or score_batch()."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pipeline = None
        return cls._instance

    def _load(self):
        if self._pipeline is None:
            logger.info("Loading FinBERT model (first call only)...")
            self._pipeline = pipeline(
                "text-classification",
                model="yiyanghkust/finbert-tone",
                return_all_scores=True,
            )
            logger.info("FinBERT model loaded.")

    def _parse_result(self, result: list[dict]) -> dict:
        """Parse a single FinBERT output into a detail dict."""
        scores = {r["label"].lower(): r["score"] for r in result}
        positive_prob = scores.get("positive", 0.0)
        negative_prob = scores.get("negative", 0.0)
        neutral_prob = scores.get("neutral", 0.0)
        composite_score = positive_prob - negative_prob

        if composite_score > 0.1:
            label = "bullish"
        elif composite_score < -0.1:
            label = "bearish"
        else:
            label = "neutral"

        return {
            "positive_prob": positive_prob,
            "negative_prob": negative_prob,
            "neutral_prob": neutral_prob,
            "composite_score": composite_score,
            "label": label,
        }

    def score_detail(self, text: str) -> dict:
        """
        Returns dict with all probabilities and classification:
        {positive_prob, negative_prob, neutral_prob, composite_score, label}
        """
        self._load()
        truncated = text[:512]
        results = self._pipeline(truncated)[0]
        return self._parse_result(results)

    def score(self, text: str) -> tuple[float, str]:
        """
        Returns (score, label).
        score in [-1, 1] = positive_prob - negative_prob
        label in {bullish, bearish, neutral}
        """
        detail = self.score_detail(text)
        return detail["composite_score"], detail["label"]

    def score_batch(self, texts: list[str]) -> list[dict]:
        """
        Batch score texts using a single pipeline call.
        Returns list of detail dicts (same format as score_detail).
        """
        if not texts:
            return []
        self._load()
        truncated = [t[:512] for t in texts]
        all_results = self._pipeline(truncated)
        return [self._parse_result(result) for result in all_results]
