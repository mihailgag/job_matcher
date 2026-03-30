from datetime import datetime

from src.scrapers.models import ScrapeRequest, BaseScraperConfig
from src.scrapers.registry import get_scraper_components
from src.protocols.repositories import RawJobAdsRepositoryProtocol, LocationMappingsRepositoryProtocol


class ScrapeRunner:
    def __init__(
        self,
        raw_job_ads_repository: RawJobAdsRepositoryProtocol | None = None,
        location_mappings_repository: LocationMappingsRepositoryProtocol | None = None,
    ) -> None:
        self.raw_job_ads_repository = raw_job_ads_repository
        self.location_mappings_repository = location_mappings_repository

    def run(
        self,
        source: str,
        job_titles: list[str],
        locations: list[str],
        execution_ts: datetime,
        scraper_config: BaseScraperConfig | None = None,
    ):
        request = ScrapeRequest(
            source=source,
            job_titles=job_titles,
            locations=locations,
            execution_ts=execution_ts,
        )

        scraper_cls, default_config_cls = get_scraper_components(source)

        if scraper_config is None:
            scraper_config = default_config_cls()

        scraper = scraper_cls(
            config=scraper_config,
            raw_job_ads_repository=self.raw_job_ads_repository,
            location_mappings_repository=self.location_mappings_repository,
        )

        return scraper.scrape(request)