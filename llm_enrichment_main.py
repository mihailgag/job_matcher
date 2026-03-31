import logging
import os

from src.core.logging_config import setup_logging
from src.database.db_manager import DBManager
from src.database.repositories.llm_repository import LLMRepository
from src.database.repositories.scoring_repository import ScoringRepository
from src.llm.models import CandidateProfile, LLMEligibilityConfig, LLMRuntimeConfig
from src.llm.prompt_builder import PromptBuilder
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
    prompt_builder = PromptBuilder()

    llm_enrichment_service = LLMEnrichmentService(
        scoring_repository=scoring_repository,
        llm_repository=llm_repository,
        prompt_builder=prompt_builder,
    )

    profile_name = "mihail_data_eng"
    score_config_hash = "9d7cee8fc0464f3f9d36cda060c4dd3f38116b3c2f426aa0cd38f31d6215bd1a"

    candidate_profile = CandidateProfile(
        profile_name=profile_name,
        profile_version_hash="mihail_profile_v1",
        summary=(
            "Senior Data/Platform Engineer with strong experience in Python, SQL, "
            "Airflow, ETL, Spark, Scala, Terraform, and GCP/Azure, Grafana, BigQuery, Lambda"
            "Composer InfluxDB. Also experienced with "
            "AWS, CI/CD, APIs, and hands-on data platform engineering. "
            "Prefers strong matches to data engineering and data platform roles."
        ),
    )

    runtime_config = LLMRuntimeConfig(
        model_name="gpt-5-mini",
        execution_mode="standard",
        prompt_template_version="job_match_v1",
        schema_version="job_match_result_v1",
        llm_config_hash="job_match_v1_gpt5mini_standard",
        max_output_tokens=800,
        temperature=0.0,
    )

    eligibility_config = LLMEligibilityConfig(
        min_score=10,
        max_age_days=30,
        allowed_work_modes=[
            WorkMode.REMOTE,
        ],
        max_description_chars=6000,
        limit=2000,
    )

    result = llm_enrichment_service.build_job_inputs_to_process(
        profile_name=profile_name,
        score_config_hash=score_config_hash,
        candidate_profile=candidate_profile,
        runtime_config=runtime_config,
        eligibility_config=eligibility_config,
        skip_cached=True,
    )

    logging.info(
        "Prepared %s LLM job inputs (eligible=%s, skipped_cached=%s)",
        len(result.jobs_to_process),
        result.eligible_jobs_count,
        result.skipped_cached_jobs_count,
    )

    for job_input in result.jobs_to_process[:3]:
        messages = prompt_builder.build_prompt_messages(job_input)

        print("=" * 100)
        print(f"RAW JOB AD ID: {job_input.raw_job_ad_id}")
        print(f"JOB CONTENT HASH: {job_input.job_content_hash}")
        print("--- SYSTEM ---")
        print(messages.system_message[:500])
        print("--- USER ---")
        print(messages.user_message[:1000])


if __name__ == "__main__":
    main()