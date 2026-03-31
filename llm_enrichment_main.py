import logging
import os

from src.core.logging_config import setup_logging
from src.database.db_manager import DBManager
from src.database.repositories.llm_repository import LLMRepository
from src.database.repositories.scoring_repository import ScoringRepository
from src.llm.models import LLMEligibilityConfig
from src.scrapers.models import WorkMode
from src.services.llm_enrichment_service import LLMEnrichmentService


def main() -> None:
    setup_logging(logging.INFO)

    dsn = os.getenv(
        "JOB_MATCHER_DSN",
        "postgresql://postgres:postgres@localhost:5432/job_matcher",
    )

    db_manager = DBManager(dsn=dsn)

    scoring_repository = ScoringRepository(db_manager)
    llm_repository = LLMRepository(db_manager)

    llm_enrichment_service = LLMEnrichmentService(
        scoring_repository=scoring_repository,
        llm_repository=llm_repository,
    )

    profile_name = "mihail_data_eng"
    score_config_hash = "9d7cee8fc0464f3f9d36cda060c4dd3f38116b3c2f426aa0cd38f31d6215bd1a"

    profile_version_hash = "profile_v1"
    llm_config_hash = "llm_config_v1"
    model_name = "gpt-5-mini"
    execution_mode = "standard"

    eligibility_config = LLMEligibilityConfig(
        min_score=14,
        max_age_days=20,
        allowed_work_modes=[
            WorkMode.REMOTE,
        ],
        max_description_chars=6000,
        limit=5000,
    )

    result = llm_enrichment_service.get_jobs_to_process(
        profile_name=profile_name,
        score_config_hash=score_config_hash,
        profile_version_hash=profile_version_hash,
        llm_config_hash=llm_config_hash,
        model_name=model_name,
        execution_mode=execution_mode,
        eligibility_config=eligibility_config,
        skip_cached=True,
    )

    logging.info(
        (
            "LLM enrichment input prepared. profile_name='%s', score_config_hash='%s', "
            "eligible_jobs=%s, jobs_to_process=%s, skipped_cached=%s"
        ),
        result.profile_name,
        result.score_config_hash,
        result.eligible_jobs_count,
        result.jobs_to_process_count,
        result.skipped_cached_jobs_count,
    )

    for job in result.jobs_to_process[:5]:
        print("=" * 80)
        print(f"Job ID: {job.raw_job_ad_id}")
        print(f"Score: {job.score}")
        print(f"Title: {job.title}")
        print(f"Company: {job.company_name}")
        print(f"Location: {job.job_location}")
        print(f"Work mode: {job.work_mode}")
        print(f"Posted date: {job.posted_date}")
        print(f"Link: {job.ad_link}")
        print(f"Description preview: {(job.description or '')[:300]}")


if __name__ == "__main__":
    main()