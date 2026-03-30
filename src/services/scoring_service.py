import logging
from dataclasses import dataclass

from src.database.repositories.raw_job_ads_repository import RawJobAdsRepository
from src.database.repositories.scoring_repository import ScoringRepository
from src.helpers.helpers import build_config_hash, build_config_json
from src.matching.job_scorer import JobScorer
from src.matching.models import JobScoreConfig
from src.scrapers.models import RawJobAd


@dataclass
class LLMEligibilityConfig:
    min_score: int
    max_age_days: int | None = None
    allowed_work_modes: list[str] | None = None
    preferred_countries: list[str] | None = None
    max_description_chars: int = 3000
    limit: int | None = None


@dataclass
class ScoringRunResult:
    profile_name: str
    config_hash: str
    loaded_jobs_count: int
    saved_scores_count: int
    eligible_jobs_count: int


class ScoringService:
    """Service responsible for saving scoring config, scoring raw ads, and selecting LLM-eligible jobs."""

    def __init__(
        self,
        raw_job_ads_repository: RawJobAdsRepository,
        scoring_repository: ScoringRepository,
    ) -> None:
        self.raw_job_ads_repository = raw_job_ads_repository
        self.scoring_repository = scoring_repository

    def run(
        self,
        profile_name: str,
        score_config: JobScoreConfig,
        llm_eligibility_config: LLMEligibilityConfig | None = None,
        raw_jobs_limit: int | None = None,
    ) -> ScoringRunResult:
        config_hash = build_config_hash(score_config)
        config_json = build_config_json(score_config)

        self.scoring_repository.save_scoring_config(
            profile_name=profile_name,
            config_hash=config_hash,
            config_json=config_json,
        )

        raw_rows = self.raw_job_ads_repository.get_raw_job_ads_for_scoring(
            profile_name=profile_name,
            config_hash=config_hash,
            limit=raw_jobs_limit,
        )

        jobs = [RawJobAd(**row) for row in raw_rows]

        logging.info("Loaded %s raw jobs to score", len(jobs))

        scorer = JobScorer(config=score_config)
        scored_jobs = scorer.score_jobs(jobs)

        saved_scores = self.scoring_repository.save_job_scores(
            scored_jobs=scored_jobs,
            profile_name=profile_name,
            config_hash=config_hash,
        )

        logging.info("Saved %s job scores", saved_scores)

        eligible_jobs_count = 0

        if llm_eligibility_config is not None:
            eligible_jobs = self.scoring_repository.get_eligible_jobs_for_llm(
                profile_name=profile_name,
                config_hash=config_hash,
                min_score=llm_eligibility_config.min_score,
                max_age_days=llm_eligibility_config.max_age_days,
                allowed_work_modes=llm_eligibility_config.allowed_work_modes,
                preferred_countries=llm_eligibility_config.preferred_countries,
                max_description_chars=llm_eligibility_config.max_description_chars,
                limit=llm_eligibility_config.limit,
            )

            eligible_jobs_count = len(eligible_jobs)

            logging.info(
                "Loaded %s eligible jobs for LLM processing with min_score=%s",
                eligible_jobs_count,
                llm_eligibility_config.min_score,
            )

        return ScoringRunResult(
            profile_name=profile_name,
            config_hash=config_hash,
            loaded_jobs_count=len(jobs),
            saved_scores_count=saved_scores,
            eligible_jobs_count=eligible_jobs_count,
        )