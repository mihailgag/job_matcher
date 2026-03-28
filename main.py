import logging
import os

from src.core.logging_config import setup_logging
from src.database.db_manager import DBManager
from src.services.scrape_runner import ScrapeRunner
from src.scrapers.models import LinkedInScraperConfig


def main():
    setup_logging(logging.INFO)

    dsn = os.getenv(
        "JOB_MATCHER_DSN",
        "postgresql://postgres:postgres@localhost:5432/job_matcher",
    )

    db_manager = DBManager(dsn=dsn)
    runner = ScrapeRunner(db_manager=db_manager)

    linkedin_config = LinkedInScraperConfig(
        profile_key="2",
        headless=False,
        max_results_per_search=400,
    )

    jobs = runner.run(
        source="linkedin",
        job_titles=["Data Engineer", "Senior Data Engineer", "Data Developer"],
        locations=["Switzerland"],
        scraper_config=linkedin_config,
        save_mode="upsert",
    )

    print(f"Scraped {len(jobs)} jobs")


if __name__ == "__main__":
    main()