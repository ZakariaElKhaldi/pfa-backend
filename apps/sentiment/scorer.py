import logging
from transformers import pipeline

logger = logging.getLogger(__name__)


class SentimentScorer:
    """Singleton FinBERT scorer. Call score() or score_batch()."""

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

    def score(self, text: str) -> tuple[float, str]:
        """
        Returns (score, label).
        score ∈ [-1, 1] = positive_prob - negative_prob
        label ∈ {bullish, bearish, neutral}
        """
        self._load()
        truncated = text[:512]
        results = self._pipeline(truncated)[0]
        scores = {r["label"].lower(): r["score"] for r in results}
        score = scores.get("positive", 0.0) - scores.get("negative", 0.0)
        if score > 0.1:
            label = "bullish"
        elif score < -0.1:
            label = "bearish"
        else:
            label = "neutral"
        return score, label

    def score_batch(self, texts: list[str]) -> list[tuple[float, str]]:
        return [self.score(t) for t in texts]
