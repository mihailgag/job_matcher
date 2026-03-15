import logging
from src.scrapers.linkedin import LinkedInScraper

SCRAPER_REGISTRY = {
    "linkedin": LinkedInScraper,
}


def get_scraper(source: str, **kwargs):
    scraper_cls = SCRAPER_REGISTRY.get(source.lower())
    if scraper_cls is None:
        raise ValueError(f"Unsupported source: {source}")
    
    logging.info(f"Scraper registry: {scraper_cls.__name__}")

    return scraper_cls(**kwargs)