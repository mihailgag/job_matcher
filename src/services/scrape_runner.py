import logging

from src.scrapers.models import ScrapeRequest
from src.scrapers.registry import get_scraper


class ScrapeRunner:
    def __init__(self, db_manager=None) -> None:
        self.db_manager = db_manager

    def run(
        self,
        source: str,
        job_titles: list[str],
        locations: list[str],
        profile_key: str = "1",
    ):
        request = ScrapeRequest(
            source=source,
            job_titles=job_titles,
            locations=locations,
        )
        logging.info(f"Using source : {request.source}, job titles: {job_titles}")

        scraper = get_scraper(
            source=source,
            profile_key=profile_key,
            db_manager=self.db_manager,
        )
        
        return scraper.scrape(request)