import logging

from src.database.repositories.llm_repository import LLMRepository
from src.database.repositories.scoring_repository import ScoringRepository
from src.llm.models import (
    EligibleJobLLM,
    LLMEligibilityConfig,
    LLMEnrichmentSelectionResult,
    CandidateProfile,
    LLMRuntimeConfig
)
from src.llm.prompt_builder import PromptBuilder


class LLMEnrichmentService:
    """
    Service responsible for selecting jobs that are eligible for LLM enrichment.

    Current scope:
    - fetch eligible jobs from scoring output
    - optionally skip jobs already cached in llm_evaluations
    - return the jobs that still need LLM processing

    Future scope:
    - build prompts
    - submit requests
    - save evaluations and usage metrics
    """
    def __init__(
        self,
        scoring_repository: ScoringRepository,
        llm_repository: LLMRepository,
        prompt_builder: PromptBuilder,
    ) -> None:
        self.scoring_repository = scoring_repository
        self.llm_repository = llm_repository
        self.prompt_builder = prompt_builder

    def get_jobs_to_process(
        self,
        profile_name: str,
        score_config_hash: str,
        profile_version_hash: str,
        llm_config_hash: str,
        model_name: str,
        execution_mode: str,
        eligibility_config: LLMEligibilityConfig,
        skip_cached: bool = True,
    ) -> LLMEnrichmentSelectionResult:
        """
        Load jobs eligible for LLM enrichment and optionally remove jobs
        that already have a cached LLM evaluation.
        """
        eligible_jobs = self.scoring_repository.get_eligible_jobs_for_llm(
            profile_name=profile_name,
            config_hash=score_config_hash,
            min_score=eligibility_config.min_score,
            max_age_days=eligibility_config.max_age_days,
            allowed_work_modes=eligibility_config.allowed_work_modes,
            preferred_countries=eligibility_config.preferred_countries,
            max_description_chars=eligibility_config.max_description_chars,
            limit=eligibility_config.limit,
        )

        logging.info(
            "Loaded %s eligible jobs for LLM enrichment for profile_name='%s' and score_config_hash='%s'",
            len(eligible_jobs),
            profile_name,
            score_config_hash,
        )

        if not skip_cached:
            return LLMEnrichmentSelectionResult(
                profile_name=profile_name,
                score_config_hash=score_config_hash,
                eligible_jobs_count=len(eligible_jobs),
                jobs_to_process_count=len(eligible_jobs),
                skipped_cached_jobs_count=0,
                jobs_to_process=eligible_jobs,
            )

        existing_job_ids = self.llm_repository.get_existing_evaluation_job_ids(
            raw_job_ad_ids=[job.raw_job_ad_id for job in eligible_jobs],
            profile_name=profile_name,
            score_config_hash=score_config_hash,
            profile_version_hash=profile_version_hash,
            llm_config_hash=llm_config_hash,
            model_name=model_name,
            execution_mode=execution_mode,
        )

        jobs_to_process = [
            job for job in eligible_jobs
            if job.raw_job_ad_id not in existing_job_ids
        ]

        skipped_cached_jobs_count = len(eligible_jobs) - len(jobs_to_process)

        logging.info(
            (
                "LLM enrichment selection summary: eligible_jobs=%s, "
                "jobs_to_process=%s, skipped_cached_jobs=%s, model_name='%s', execution_mode='%s'"
            ),
            len(eligible_jobs),
            len(jobs_to_process),
            skipped_cached_jobs_count,
            model_name,
            execution_mode,
        )

        return LLMEnrichmentSelectionResult(
            profile_name=profile_name,
            score_config_hash=score_config_hash,
            eligible_jobs_count=len(eligible_jobs),
            jobs_to_process_count=len(jobs_to_process),
            skipped_cached_jobs_count=skipped_cached_jobs_count,
            jobs_to_process=jobs_to_process,
        )
    
    def build_job_inputs_to_process(
        self,
        profile_name: str,
        score_config_hash: str,
        candidate_profile: CandidateProfile,
        runtime_config: LLMRuntimeConfig,
        eligibility_config: LLMEligibilityConfig,
        skip_cached: bool = True,
    ) -> LLMEnrichmentSelectionResult:
        selection = self.get_jobs_to_process(
            profile_name=profile_name,
            score_config_hash=score_config_hash,
            profile_version_hash=candidate_profile.profile_version_hash,
            llm_config_hash=runtime_config.llm_config_hash,
            model_name=runtime_config.model_name,
            execution_mode=runtime_config.execution_mode,
            eligibility_config=eligibility_config,
            skip_cached=skip_cached,
        )

        job_inputs = [
            self.prompt_builder.build_job_input(
                job=job,
                candidate_profile=candidate_profile,
                score_config_hash=score_config_hash,
                runtime_config=runtime_config,
            )
            for job in selection.jobs_to_process
        ]

        return LLMEnrichmentSelectionResult(
            profile_name=selection.profile_name,
            score_config_hash=selection.score_config_hash,
            eligible_jobs_count=selection.eligible_jobs_count,
            jobs_to_process_count=selection.jobs_to_process_count,
            skipped_cached_jobs_count=selection.skipped_cached_jobs_count,
            jobs_to_process=job_inputs,
        )