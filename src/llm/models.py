from dataclasses import dataclass
from typing import Optional, Literal, Any
from datetime import datetime, date
from src.scrapers.models import WorkMode

ExecutionMode = Literal["standard", "batch"]
FitLabel = Literal["strong_fit", "medium_fit", "weak_fit", "not_fit"]
RemoteType = Literal["remote", "hybrid", "on_site", "unknown"]
Seniority = Literal["junior", "mid", "senior", "lead", "staff", "principal", "unknown"]
SalaryPeriod = Literal["hour", "day", "month", "year", "unknown"]


@dataclass(frozen=True)
class CandidateProfile:
    profile_name: str
    profile_version_hash: str
    summary: str

@dataclass(frozen=True)
class LLMRuntimeConfig:
    model_name: str
    execution_mode: ExecutionMode
    prompt_template_version: str
    schema_version: str
    llm_config_hash: str
    max_output_tokens: int = 800
    temperature: float = 0.0

@dataclass(frozen=True)
class LLMJobInput:
    raw_job_ad_id: int
    profile_name: str
    score_config_hash: str
    profile_version_hash: str
    llm_config_hash: str
    model_name: str
    execution_mode: ExecutionMode
    prompt_template_version: str
    schema_version: str
    job_content_hash: str

    title: str | None
    company_name: str | None
    job_location: str | None
    work_mode: str | None
    ad_link: str | None
    posted_date: date | None
    description: str | None

    candidate_profile_summary: str

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


@dataclass(frozen=True)
class SalaryExtraction:
    salary_mentioned: bool
    min: float | None
    max: float | None
    currency: str | None
    period: SalaryPeriod | None
    raw_text: str | None


@dataclass(frozen=True)
class LLMParsedResult:
    raw_job_ad_id: int
    fit_score: int
    fit_label: FitLabel
    recommended: bool
    confidence: float
    summary: str
    fit_reasons: list[str]

    salary: SalaryExtraction

    remote_type: RemoteType
    seniority: Seniority


@dataclass(frozen=True)
class LLMEvaluationRecord:
    raw_job_ad_id: int
    profile_name: str
    score_config_hash: str
    profile_version_hash: str
    llm_config_hash: str
    model_name: str
    execution_mode: ExecutionMode
    prompt_template_version: str
    schema_version: str
    job_content_hash: str

    fit_score: int
    fit_label: FitLabel
    recommended: bool
    confidence: float
    summary: str
    fit_reasons: list[str]

    salary_mentioned: bool
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    salary_period: SalaryPeriod | None
    salary_raw_text: str | None

    remote_type: RemoteType
    seniority: Seniority

    raw_result_json: dict[str, Any]
    request_status: str = "completed"


@dataclass(frozen=True)
class LLMRequestRecord:
    raw_job_ad_id: int
    profile_name: str
    score_config_hash: str
    profile_version_hash: str
    llm_config_hash: str

    model_name: str
    execution_mode: ExecutionMode
    prompt_template_version: str
    schema_version: str

    provider_request_id: str | None = None
    batch_id: str | None = None
    batch_custom_id: str | None = None

    request_payload_json: dict[str, Any] | None = None
    response_payload_json: dict[str, Any] | None = None

    request_status: str = "queued"
    error_type: str | None = None
    error_message: str | None = None
    retry_count: int = 0

    sent_at: datetime | None = None
    finished_at: datetime | None = None


@dataclass(frozen=True)
class LLMUsageMetricsRecord:
    llm_request_id: int
    raw_job_ad_id: int
    profile_name: str
    score_config_hash: str
    model_name: str
    execution_mode: ExecutionMode

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cached_input_tokens: int = 0

    estimated_input_cost_usd: float | None = None
    estimated_output_cost_usd: float | None = None
    estimated_total_cost_usd: float | None = None


@dataclass(frozen=True)
class LLMEligibilityConfig:
    min_score: int
    max_age_days: int | None = None
    allowed_work_modes: list[str] | None = None
    preferred_countries: list[str] | None = None
    max_description_chars: int = 3000
    limit: int | None = None


@dataclass(frozen=True)
class LLMEnrichmentSelectionResult:
    profile_name: str
    score_config_hash: str
    eligible_jobs_count: int
    jobs_to_process_count: int
    skipped_cached_jobs_count: int
    jobs_to_process: list[EligibleJobLLM]


@dataclass(frozen=True)
class PromptMessages:
    system_message: str
    user_message: str


@dataclass(frozen=True)
class LLMPreparedInputsResult:
    profile_name: str
    score_config_hash: str
    eligible_jobs_count: int
    jobs_to_process_count: int
    skipped_cached_jobs_count: int
    job_inputs: list[LLMJobInput]