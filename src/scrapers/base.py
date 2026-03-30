from abc import abstractmethod
from typing import Optional
from src.scrapers.models import ScrapeRequest, RawJobAd

from src.database.repositories.location_mappings_repository import (
    LocationMappingsRepository,
)
from src.database.repositories.raw_job_ads_repository import RawJobAdsRepository


class BaseScraper:
    def __init__(
        self,
        raw_job_ads_repository: Optional[RawJobAdsRepository] = None,
        location_mappings_repository: Optional[LocationMappingsRepository] = None,
    ) -> None:
        self.raw_job_ads_repository = raw_job_ads_repository
        self.location_mappings_repository = location_mappings_repository

    @abstractmethod
    def scrape(self, request: "ScrapeRequest") -> list["RawJobAd"]:
        """Run the scraping process and return raw ads."""
        raise NotImplementedError