from abc import ABC, abstractmethod


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self, symbol: str) -> list[dict]:
        """Return list of dicts with keys: source, external_id, content, posted_at"""
        ...
