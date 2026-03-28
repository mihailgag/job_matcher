import logging 

from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.models import LinkedInScraperConfig, BaseScraperConfig
from src.scrapers.base import BaseScraper

SCRAPER_REGISTRY = {
    "linkedin": {
        "scraper_class": LinkedInScraper,
        "config_class": LinkedInScraperConfig,
    },
}

def get_scraper_components(
    source: str,
) -> tuple[type[BaseScraper], type[BaseScraperConfig]]:
    item = SCRAPER_REGISTRY.get(source.lower())
    if item is None:
        raise ValueError(f"Unsupported source: {source}")

    logging.info(f"Scraper registry: {item['scraper_class'].__name__}")

    return item["scraper_class"], item["config_class"]
