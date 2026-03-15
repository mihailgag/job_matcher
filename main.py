import logging

from src.core.logging_config import setup_logging
from src.services.scrape_runner import ScrapeRunner

def main():
    setup_logging(logging.INFO)

    runner = ScrapeRunner(db_manager=None)

    jobs = runner.run(
        source="linkedin",
        job_titles=["Data Engineer"],
        locations=["106693272"], 
        profile_key="2",
    )

    for job in jobs[:3]:
        print(job)

if __name__ == "__main__":
    main()

