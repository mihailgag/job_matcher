import logging

from src.scrapers.models import ScrapeRequest
from src.scrapers.registry import get_scraper
from src.database.db_manager import DBManager


class ScrapeRunner:
    def __init__(self, db_manager: DBManager=None) -> None:
        self.db_manager = db_manager

    def run(
        self,
        source: str,
        job_titles: list[str],
        locations: list[str],
        profile_key: str = "1",
        save_mode: str = "upsert",
    ):
        request = ScrapeRequest(
            source=source,
            job_titles=job_titles,
            locations=locations,
        )
        logging.info(
            "Using source=%s, job_titles=%s, locations=%s",
            request.source,
            job_titles,
            locations,
        )

        scraper = get_scraper(
            source=source,
            profile_key=profile_key,
            db_manager=self.db_manager,
        )

        jobs = scraper.scrape(request)

        logging.info("Scraper returned %s jobs.", len(jobs))

        if self.db_manager is not None:
            if source == "linkedin":
                self.db_manager.save_raw_job_ads(jobs=jobs, mode=save_mode)
            else:
                self.db_manager.save_rows(
                    table_name="raw_job_ads",
                    rows=jobs,
                    mode=save_mode,
                    conflict_columns=["source", "ad_id"],
                )

        return jobs