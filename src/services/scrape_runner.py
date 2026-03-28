from datetime import datetime

from src.scrapers.models import ScrapeRequest, BaseScraperConfig
from src.scrapers.registry import get_scraper_components
from src.database.db_manager import DBManager


class ScrapeRunner:
    def __init__(self, db_manager: DBManager | None = None) -> None:
        self.db_manager = db_manager

    def run(
        self,
        source: str,
        job_titles: list[str],
        locations: list[str],
        execution_ts: datetime,
        scraper_config: BaseScraperConfig | None = None,
        save_mode: str = "upsert",
    ):
        request = ScrapeRequest(
            source=source,
            job_titles=job_titles,
            locations=locations,
            execution_ts=execution_ts
        )

        scraper_cls, default_config_cls = get_scraper_components(source)

        if scraper_config is None:
            scraper_config = default_config_cls()

        scraper = scraper_cls(
            config=scraper_config,
            db_manager=self.db_manager,
        )

        jobs = scraper.scrape(request)

        if self.db_manager is not None:
            self.db_manager.save_raw_job_ads(jobs=jobs, mode=save_mode)

        return jobs