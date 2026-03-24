import logging
import os

from src.core.logging_config import setup_logging
from src.database.db_manager import DBManager
from src.services.scrape_runner import ScrapeRunner


def main():
    setup_logging(logging.INFO)

    dsn = os.getenv(
        "JOB_MATCHER_DSN",
        "postgresql://postgres:postgres@localhost:5432/job_matcher",
    )

    db_manager = DBManager(dsn=dsn)

    runner = ScrapeRunner(db_manager=db_manager)

    jobs = runner.run(
        source="linkedin",
        job_titles=["Data Engineer"],
        locations=["Germany", "Switzerland"],
        profile_key="2",
        save_mode="upsert",
    )

if __name__ == "__main__":
    main()