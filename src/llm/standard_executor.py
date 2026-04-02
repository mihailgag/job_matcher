from datetime import datetime, timezone

from src.database.repositories.llm_repository import LLMRepository
from src.llm.client import OpenAIClient
from src.llm.cost_tracking import estimate_cost
from src.llm.models import (
    LLMJobInput,
    LLMRequestRecord,
    LLMRuntimeConfig,
    LLMEvaluationRecord,
    LLMUsageMetricsRecord,
)
from src.llm.prompt_builder import PromptBuilder
from src.llm.output_schema import build_job_match_schema


class StandardLLMExecutor:
    def __init__(
        self,
        llm_repository: LLMRepository,
        openai_client: OpenAIClient,
        prompt_builder: PromptBuilder,
    ) -> None:
        self.llm_repository = llm_repository
        self.openai_client = openai_client
        self.prompt_builder = prompt_builder

    def execute_one(
        self,
        job_input: LLMJobInput,
        runtime_config: LLMRuntimeConfig,
    ) -> int:
        messages = self.prompt_builder.build_prompt_messages(job_input)
        schema = build_job_match_schema(job_input.schema_version)

        now = datetime.now(timezone.utc)

        request_record = LLMRequestRecord(
            raw_job_ad_id=job_input.raw_job_ad_id,
            profile_name=job_input.profile_name,
            score_config_hash=job_input.score_config_hash,
            profile_version_hash=job_input.profile_version_hash,
            llm_config_hash=job_input.llm_config_hash,
            model_name=job_input.model_name,
            execution_mode=job_input.execution_mode,
            prompt_template_version=job_input.prompt_template_version,
            schema_version=job_input.schema_version,
            request_payload_json={
                "system_message": messages.system_message,
                "user_message": messages.user_message,
                "schema": schema,
                "model_name": runtime_config.model_name,
                "temperature": runtime_config.temperature,
                "max_output_tokens": runtime_config.max_output_tokens,
            },
            request_status="submitted",
            sent_at=now,
        )

        request_id = self.llm_repository.insert_request_returning_id(request_record)

        try:
            response = self.openai_client.create_job_match_response(
                model_name=runtime_config.model_name,
                system_message=messages.system_message,
                user_message=messages.user_message,
                schema=schema,
                temperature=runtime_config.temperature,
                max_output_tokens=runtime_config.max_output_tokens,
            )

            parsed = response.parsed_result

            evaluation_record = LLMEvaluationRecord(
                raw_job_ad_id=job_input.raw_job_ad_id,
                profile_name=job_input.profile_name,
                score_config_hash=job_input.score_config_hash,
                profile_version_hash=job_input.profile_version_hash,
                llm_config_hash=job_input.llm_config_hash,
                model_name=job_input.model_name,
                execution_mode=job_input.execution_mode,
                prompt_template_version=job_input.prompt_template_version,
                schema_version=job_input.schema_version,
                job_content_hash=job_input.job_content_hash,
                fit_score=parsed.fit_score,
                fit_label=parsed.fit_label,
                recommended=parsed.recommended,
                confidence=parsed.confidence,
                summary=parsed.summary,
                fit_reasons=parsed.fit_reasons,
                salary_mentioned=parsed.salary.salary_mentioned,
                salary_min=parsed.salary.min,
                salary_max=parsed.salary.max,
                salary_currency=parsed.salary.currency,
                salary_period=parsed.salary.period,
                salary_raw_text=parsed.salary.raw_text,
                remote_type=parsed.remote_type,
                remote_scope=parsed.remote_scope,
                remote_scope_details=parsed.remote_scope_details,
                visa_sponsorship=parsed.visa_sponsorship,
                visa_sponsorship_details=parsed.visa_sponsorship_details,
                relocation_support=parsed.relocation_support,
                relocation_support_details=parsed.relocation_support_details,
                seniority=parsed.seniority,
                raw_result_json=response.raw_response_json or {},
                request_status="completed",
            )

            self.llm_repository.save_evaluation(evaluation_record)

            input_cost, output_cost, total_cost = estimate_cost(
                model_name=job_input.model_name,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cached_input_tokens=response.cached_input_tokens,
            )

            usage_record = LLMUsageMetricsRecord(
                llm_request_id=request_id,
                raw_job_ad_id=job_input.raw_job_ad_id,
                profile_name=job_input.profile_name,
                score_config_hash=job_input.score_config_hash,
                model_name=job_input.model_name,
                execution_mode=job_input.execution_mode,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
                cached_input_tokens=response.cached_input_tokens,
                estimated_input_cost_usd=input_cost,
                estimated_output_cost_usd=output_cost,
                estimated_total_cost_usd=total_cost,
            )

            self.llm_repository.save_usage_metrics(usage_record)

            self.llm_repository.update_request_status(
                request_id=request_id,
                request_status="completed",
                provider_request_id=response.provider_request_id,
                response_payload_json=response.raw_response_json,
                finished_at=datetime.now(timezone.utc),
            )

            return request_id

        except Exception as exc:
            self.llm_repository.update_request_status(
                request_id=request_id,
                request_status="failed",
                error_type=type(exc).__name__,
                error_message=str(exc),
                finished_at=datetime.now(timezone.utc),
            )
            raise