import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import requests

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    source = "unknown"
    timeout = 10
    retry_statuses = {429, 500, 502, 503, 504}

    @abstractmethod
    def fetch(self, symbol: str) -> list[dict]:
        """
        Return normalized posts with source, external_id, title, url,
        content, posted_at, and optional metadata.
        """
        ...

    def request_json(
        self,
        method: str,
        url: str,
        *,
        retries: int = 2,
        backoff_seconds: float = 0.5,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        kwargs.setdefault("timeout", self.timeout)

        for attempt in range(retries + 1):
            try:
                response = requests.request(method, url, **kwargs)
                if response.status_code in self.retry_statuses and attempt < retries:
                    retry_after = response.headers.get("Retry-After")
                    delay = self._retry_delay(retry_after, backoff_seconds, attempt)
                    logger.warning(
                        "%s fetch received HTTP %s for %s; retrying in %.2fs",
                        self.source,
                        response.status_code,
                        url,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                if response.status_code == 429:
                    logger.warning("%s fetch rate limited for %s", self.source, url)
                    return None

                response.raise_for_status()
                return response.json()
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt < retries:
                    delay = backoff_seconds * (2**attempt)
                    logger.warning(
                        "%s fetch network error for %s; retrying in %.2fs: %s",
                        self.source,
                        url,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                    continue
                logger.warning("%s fetch network error for %s: %s", self.source, url, exc)
                return None
            except ValueError as exc:
                logger.warning("%s fetch returned malformed JSON for %s: %s", self.source, url, exc)
                return None
            except requests.HTTPError as exc:
                logger.warning("%s fetch HTTP error for %s: %s", self.source, url, exc)
                return None
            except requests.RequestException as exc:
                logger.warning("%s fetch request failed for %s: %s", self.source, url, exc)
                return None

        return None

    def _retry_delay(self, retry_after: str | None, backoff_seconds: float, attempt: int) -> float:
        if retry_after:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass
        return backoff_seconds * (2**attempt)
