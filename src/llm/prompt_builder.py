import hashlib
import json
from datetime import date
from typing import Any

from src.llm.models import (
    CandidateProfile,
    EligibleJobLLM,
    LLMJobInput,
    LLMRuntimeConfig,
    PromptMessages,
)
from src.llm.prompt_templates import get_system_prompt


class PromptBuilder:
    """Build normalized LLM inputs and prompt messages from eligible jobs."""

    def build_job_input(
        self,
        job: EligibleJobLLM,
        candidate_profile: CandidateProfile,
        score_config_hash: str,
        runtime_config: LLMRuntimeConfig,
    ) -> LLMJobInput:
        job_content_hash = self._build_job_content_hash(job)

        return LLMJobInput(
            raw_job_ad_id=job.raw_job_ad_id,
            profile_name=candidate_profile.profile_name,
            score_config_hash=score_config_hash,
            profile_version_hash=candidate_profile.profile_version_hash,
            llm_config_hash=runtime_config.llm_config_hash,
            model_name=runtime_config.model_name,
            execution_mode=runtime_config.execution_mode,
            prompt_template_version=runtime_config.prompt_template_version,
            schema_version=runtime_config.schema_version,
            job_content_hash=job_content_hash,
            title=job.title,
            company_name=job.company_name,
            job_location=job.job_location,
            work_mode=job.work_mode,
            ad_link=job.ad_link,
            posted_date=job.posted_date,
            description=job.description,
            candidate_profile_summary=candidate_profile.summary,
        )

    def build_prompt_messages(
        self,
        job_input: LLMJobInput,
    ) -> PromptMessages:
        system_message = get_system_prompt(job_input.prompt_template_version)

        posted_date_text = self._format_date(job_input.posted_date)

        user_message = f"""
        CANDIDATE PROFILE
        Profile name: {job_input.profile_name}
        Profile version hash: {job_input.profile_version_hash}

        Summary:
        {job_input.candidate_profile_summary}

        JOB
        Raw job ad ID: {job_input.raw_job_ad_id}
        Title: {job_input.title or ""}
        Company: {job_input.company_name or ""}
        Location: {job_input.job_location or ""}
        Work mode: {job_input.work_mode or ""}
        Posted date: {posted_date_text}
        Source URL: {job_input.ad_link or ""}

        DESCRIPTION
        {job_input.description or ""}
        """.strip()

        return PromptMessages(
            system_message=system_message,
            user_message=user_message,
        )

    @staticmethod
    def _build_job_content_hash(job: EligibleJobLLM) -> str:
        payload = {
            "title": job.title or "",
            "company_name": job.company_name or "",
            "job_location": job.job_location or "",
            "work_mode": job.work_mode or "",
            "ad_link": job.ad_link or "",
            "posted_date": job.posted_date.isoformat() if job.posted_date else None,
            "description": job.description or "",
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _format_date(value: date | None) -> str:
        if value is None:
            return ""
        return value.isoformat()