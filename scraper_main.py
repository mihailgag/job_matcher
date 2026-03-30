import logging
import os
from datetime import datetime, timezone

from src.core.logging_config import setup_logging
from src.database.db_manager import DBManager
from src.database.repositories.location_mappings_repository import (
    LocationMappingsRepository,
)
from src.database.repositories.raw_job_ads_repository import RawJobAdsRepository
from src.services.scrape_runner import ScrapeRunner
from src.scrapers.models import LinkedInScraperConfig, ScrapeRefreshMode, ScrapeRefreshPolicy


def main() -> None:
    setup_logging(logging.INFO)

    dsn = os.getenv(
        "JOB_MATCHER_DSN",
        "postgresql://postgres:postgres@localhost:5432/job_matcher",
    )

    db_manager = DBManager(dsn=dsn)

    raw_job_ads_repository = RawJobAdsRepository(db_manager)
    location_mappings_repository = LocationMappingsRepository(db_manager)

    scrape_runner = ScrapeRunner(
        raw_job_ads_repository=raw_job_ads_repository,
        location_mappings_repository=location_mappings_repository,
    )
    linkedin_config = LinkedInScraperConfig(
        profile_key="2",
        headless=False,
        max_results_per_search=25,
        refresh_policy=ScrapeRefreshPolicy(
        mode=ScrapeRefreshMode.STALE_OR_NEW,
        stale_after_days=10,
        )
    )

    jobs = scrape_runner.run(
        source="linkedin",
        job_titles=["data engineer"],
        locations=["Netherlands", "Scotland", "Ukraine", "Israel", "European Union"],
        execution_ts=datetime.now(timezone.utc),
        scraper_config=linkedin_config
    )

    print(f"Collected {len(jobs)} jobs")


if __name__ == "__main__":
    main()



