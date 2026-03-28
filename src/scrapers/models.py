from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class ScrapeRequest:
    source: str
    job_titles: list[str]
    locations: list[str] = field(default_factory=list)

@dataclass
class RawJobAd:
    source: str
    ad_id: str
    ad_link: str
    title: Optional[str] = None
    company_name: Optional[str] = None
    company_info: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    posted_at: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseScraperConfig:
    pass

@dataclass
class LinkedInScraperConfig(BaseScraperConfig):
    profile_key: str = "1"
    headless: bool = False
    max_results_per_search: int = 25
