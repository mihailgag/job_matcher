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
    title: Optional[str]
    company_name: Optional[str]
    company_info: Optional[str]
    metadata: dict[str, Any] = field(default_factory=dict)