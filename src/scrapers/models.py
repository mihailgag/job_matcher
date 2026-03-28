from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime


@dataclass
class ScrapeRequest:
    source: str
    execution_ts: datetime
    job_titles: list[str]
    locations: list[str] = field(default_factory=list)
    
@dataclass
class RawJobAd:
    id: Optional[int] = None
    source: str = ""
    ad_id: str= ""
    ad_link: str= ""
    title: Optional[str] = None
    company_name: Optional[str] = None
    input_location: Optional[str] = None
    job_location: Optional[str] = None
    work_mode: Optional[str] = None
    posted_date: Optional[int] = None
    description: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseScraperConfig:
    pass

@dataclass
class LinkedInScraperConfig(BaseScraperConfig):
    profile_key: str = "1"
    headless: bool = False
    max_results_per_search: int = 25