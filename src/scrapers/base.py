from abc import ABC, abstractmethod
from typing import Optional
from src.scrapers.models import ScrapeRequest, RawJobAd


class BaseScraper(ABC):
    def __init__(self, db_manager: Optional[object] = None) -> None:
        self.db_manager = db_manager

    @abstractmethod
    def scrape(self, request: "ScrapeRequest") -> list["RawJobAd"]:
        """Run the scraping process and return raw ads."""
        raise NotImplementedError