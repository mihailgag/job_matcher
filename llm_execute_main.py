import logging
import os

from src.core.logging_config import setup_logging
from src.database.db_manager import DBManager
from src.database.repositories.llm_repository import LLMRepository
from src.database.repositories.scoring_repository import ScoringRepository
from src.llm.client import OpenAIClient
from src.llm.models import CandidateProfile, LLMEligibilityConfig, LLMRuntimeConfig, ExecutionMode
from src.llm.prompt_builder import PromptBuilder
from src.llm.standard_executor import StandardLLMExecutor
from src.scrapers.models import WorkMode
from src.services.llm_enrichment_service import LLMEnrichmentService
from src.services.llm_execution_service import LLMExecutionService


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
    openai_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))

    llm_enrichment_service = LLMEnrichmentService(
        scoring_repository=scoring_repository,
        llm_repository=llm_repository,
        prompt_builder=prompt_builder,
    )

    standard_executor = StandardLLMExecutor(
        llm_repository=llm_repository,
        openai_client=openai_client,
        prompt_builder=prompt_builder,
    )

    execution_service = LLMExecutionService(
        standard_executor=standard_executor,
    )

    profile_name = "mihail_data_eng"

    latest_config = scoring_repository.get_latest_scoring_config(profile_name=profile_name)
    if latest_config is None:
        raise ValueError(f"No scoring config found for profile_name='{profile_name}'")
    
    score_config_hash = latest_config["config_hash"]

    candidate_profile = CandidateProfile(
        profile_name=profile_name,
        profile_version_hash="mihail_profile_v1",
        summary=(
            "Senior Data/Platform Engineer with strong experience in Python, SQL, "
            "Airflow, ETL, Spark, Scala, Terraform, BigQuery,Composer, Dataproc, AWS Glue, AWS Lambda and GCP/Azure. Also experienced with "
            "AWS, CI/CD, APIs, GitHub Workflows, GitLab Ci/CD container registires, Docker, and hands-on data platform engineering."
        ),
    )

    runtime_config = LLMRuntimeConfig(
        model_name="gpt-4.1-mini",
        execution_mode=ExecutionMode.STANDARD,
        prompt_template_version="job_match_v1",
        schema_version="job_match_result_v1",
        llm_config_hash="job_match_v1_gpt41mini_standard",
        max_output_tokens=800,
        temperature=0.0,
    )

    eligibility_config = LLMEligibilityConfig(
        min_score=14,
        max_age_days=30,
        allowed_work_modes=[WorkMode.REMOTE],
        preferred_countries=["United Kingdom", "Switzerland"],
        max_description_chars=6000,
        limit=10,
    )

    prepared = llm_enrichment_service.build_job_inputs_to_process(
        profile_name=profile_name,
        score_config_hash=score_config_hash,
        candidate_profile=candidate_profile,
        runtime_config=runtime_config,
        eligibility_config=eligibility_config,
        skip_cached=True,
    )

    logging.info("Prepared %s jobs for execution", len(prepared.jobs_to_process))

    execution_service.execute_prepared_inputs(
        prepared_inputs=prepared,
        runtime_config=runtime_config,
    )


if __name__ == "__main__":
    main()

