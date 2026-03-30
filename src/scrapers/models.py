from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from enum import StrEnum


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
    first_scraped_at: Optional[datetime] = None
    last_scraped_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


@dataclass
class BaseScraperConfig:
    pass

class WriteMode(StrEnum):
    APPEND = "append"
    UPSERT = "upsert"


class ScrapeRefreshMode(StrEnum):
    NEW_ONLY = "new_only"
    STALE_OR_NEW = "stale_or_new"
    ALL = "all"


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"


@dataclass
class ScrapeRefreshPolicy:
    mode: ScrapeRefreshMode = ScrapeRefreshMode.STALE_OR_NEW
    stale_after_days: int = 3

@dataclass
class LinkedInScraperConfig(BaseScraperConfig):
    profile_key: str = "1"
    headless: bool = False
    max_results_per_search: int = 25
    refresh_policy: ScrapeRefreshPolicy = field(
        default_factory=ScrapeRefreshPolicy
    )
