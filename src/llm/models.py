from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from src.scrapers.models import WorkMode


@dataclass
class EligibleJobLLM:
    raw_job_ad_id: str
    score: int
    title: Optional[str]
    company_name: Optional[str]
    job_location: Optional[str]
    work_mode: Optional[WorkMode]
    ad_link: Optional[str]
    posted_date: Optional[datetime]
    description: Optional[str]
    job_location: Optional[str]