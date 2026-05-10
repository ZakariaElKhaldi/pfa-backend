import logging
import time
from datetime import datetime, timezone as dt_timezone

from asgiref.sync import sync_to_async
from decouple import config

from apps.social.cleaner import clean_text, is_quality_post

logger = logging.getLogger(__name__)


class AlpacaNewsStreamManager:
    """Long-running Alpaca news websocket ingester with reconnect/backoff."""

    SOURCE = "news_alpaca"

    def __init__(self) -> None:
        self.api_key = config("ALPACA_API_KEY", default="")
        self.secret_key = config("ALPACA_SECRET_KEY", default="")

    def get_symbols(self) -> list[str]:
        from apps.tickers.models import Ticker

        return list(Ticker.objects.values_list("symbol", flat=True))

    @staticmethod
    def _extract_symbols(news) -> list[str]:
        symbols = getattr(news, "symbols", None) or []
        if isinstance(symbols, str):
            return [symbols]
        if isinstance(symbols, list):
            return [symbol for symbol in symbols if isinstance(symbol, str) and symbol]
        return []

    @staticmethod
    def _extract_content(news) -> str:
        content = getattr(news, "summary", None) or getattr(news, "headline", None) or ""
        return str(content)

    @staticmethod
    def _extract_external_id(news) -> str:
        return str(getattr(news, "id", ""))

    @staticmethod
    def _extract_posted_at(news) -> datetime:
        created_at = getattr(news, "created_at", None)
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                return created_at.replace(tzinfo=dt_timezone.utc)
            return created_at
        return datetime.now(tz=dt_timezone.utc)

    async def handle_news(self, news) -> None:
        from apps.pipeline.pipeline import run_pipeline_for_ticker
        from apps.social.models import SocialPost
        from apps.tickers.models import Ticker

        symbols = self._extract_symbols(news)
        if not symbols:
            return

        external_id = self._extract_external_id(news)
        if not external_id:
            return

        content = self._extract_content(news)
        cleaned = clean_text(content)
        if not is_quality_post(cleaned):
            return

        posted_at = self._extract_posted_at(news)
        title = str(getattr(news, "headline", "") or "")[:500]
        url = str(getattr(news, "url", "") or "")[:1000]

        for symbol in symbols:
            try:
                ticker = await sync_to_async(Ticker.objects.get)(symbol=symbol)
            except Ticker.DoesNotExist:
                continue

            post, created = await sync_to_async(SocialPost.objects.get_or_create)(
                ticker=ticker,
                source=self.SOURCE,
                external_id=external_id,
                defaults={
                    "title": title or None,
                    "url": url or None,
                    "content": content,
                    "cleaned_text": cleaned,
                    "posted_at": posted_at,
                },
            )

            if not created:
                continue

            await sync_to_async(run_pipeline_for_ticker)(symbol)

    def run(self) -> None:
        from alpaca.data.live import NewsDataStream

        backoff = 5
        while True:
            symbols = self.get_symbols()
            if not symbols:
                logger.info("No tracked tickers for news stream; retrying in 60s")
                time.sleep(60)
                continue

            try:
                stream = NewsDataStream(self.api_key, self.secret_key)
                stream.subscribe_news(self.handle_news, *symbols)
                logger.info("Alpaca news stream started for %d symbols", len(symbols))
                stream.run()
                backoff = 5
            except Exception as exc:
                logger.exception(
                    "Alpaca news stream failed; reconnecting in %ss: %s",
                    backoff,
                    exc,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)
