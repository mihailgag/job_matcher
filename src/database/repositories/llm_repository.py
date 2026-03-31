from typing import Any, Iterable

from src.database.db_manager import DBManager
from src.scrapers.models import WriteMode
from src.llm.models import (
    LLMEvaluationRecord,
    LLMRequestRecord,
    LLMUsageMetricsRecord,
)


class LLMRepository:
    """Repository responsible for LLM evaluations, request logs, and usage metrics."""

    def __init__(self, db_manager: DBManager) -> None:
        self.db_manager = db_manager

    def get_existing_evaluation(
        self,
        raw_job_ad_id: int,
        profile_name: str,
        score_config_hash: str,
        profile_version_hash: str,
        llm_config_hash: str,
        model_name: str,
        execution_mode: str,
        job_content_hash: str,
    ) -> dict[str, Any] | None:
        """
        Return an existing LLM evaluation row if one already exists for the
        same job/profile/config/model/content combination.
        """
        sql = """
            SELECT
                id,
                raw_job_ad_id,
                profile_name,
                score_config_hash,
                profile_version_hash,
                llm_config_hash,
                model_name,
                execution_mode,
                prompt_template_version,
                schema_version,
                job_content_hash,
                fit_score,
                fit_label,
                recommended,
                confidence,
                summary,
                fit_reasons,
                salary_mentioned,
                salary_min,
                salary_max,
                salary_currency,
                salary_period,
                salary_raw_text,
                remote_type,
                seniority,
                raw_result_json,
                request_status,
                processed_at,
                created_at,
                updated_at
            FROM llm_evaluations
            WHERE raw_job_ad_id = %s
              AND profile_name = %s
              AND score_config_hash = %s
              AND profile_version_hash = %s
              AND llm_config_hash = %s
              AND model_name = %s
              AND execution_mode = %s
              AND job_content_hash = %s
            LIMIT 1
        """

        rows = self.db_manager.fetch_all(
            sql,
            (
                raw_job_ad_id,
                profile_name,
                score_config_hash,
                profile_version_hash,
                llm_config_hash,
                model_name,
                execution_mode,
                job_content_hash,
            ),
        )

        return rows[0] if rows else None

    def save_evaluation(
        self,
        evaluation: LLMEvaluationRecord,
    ) -> int:
        """Persist a parsed LLM evaluation result."""
        rows = [
            {
                "raw_job_ad_id": evaluation.raw_job_ad_id,
                "profile_name": evaluation.profile_name,
                "score_config_hash": evaluation.score_config_hash,
                "profile_version_hash": evaluation.profile_version_hash,
                "llm_config_hash": evaluation.llm_config_hash,
                "model_name": evaluation.model_name,
                "execution_mode": evaluation.execution_mode,
                "prompt_template_version": evaluation.prompt_template_version,
                "schema_version": evaluation.schema_version,
                "job_content_hash": evaluation.job_content_hash,
                "fit_score": evaluation.fit_score,
                "fit_label": evaluation.fit_label,
                "recommended": evaluation.recommended,
                "confidence": evaluation.confidence,
                "summary": evaluation.summary,
                "fit_reasons": evaluation.fit_reasons,
                "salary_mentioned": evaluation.salary_mentioned,
                "salary_min": evaluation.salary_min,
                "salary_max": evaluation.salary_max,
                "salary_currency": evaluation.salary_currency,
                "salary_period": evaluation.salary_period,
                "salary_raw_text": evaluation.salary_raw_text,
                "remote_type": evaluation.remote_type,
                "seniority": evaluation.seniority,
                "raw_result_json": evaluation.raw_result_json,
                "request_status": evaluation.request_status,
            }
        ]

        return self.db_manager.save_rows(
            table_name="llm_evaluations",
            rows=rows,
            mode=WriteMode.UPSERT,
            conflict_columns=[
                "raw_job_ad_id",
                "profile_name",
                "score_config_hash",
                "profile_version_hash",
                "llm_config_hash",
                "model_name",
                "execution_mode",
                "job_content_hash",
            ],
            update_columns=[
                "prompt_template_version",
                "schema_version",
                "fit_score",
                "fit_label",
                "recommended",
                "confidence",
                "summary",
                "fit_reasons",
                "salary_mentioned",
                "salary_min",
                "salary_max",
                "salary_currency",
                "salary_period",
                "salary_raw_text",
                "remote_type",
                "seniority",
                "raw_result_json",
                "request_status",
            ],
        )

    def save_request(
        self,
        request: LLMRequestRecord,
    ) -> int:
        """Persist an LLM request/debug record."""
        rows = [
            {
                "raw_job_ad_id": request.raw_job_ad_id,
                "llm_evaluation_id": request.llm_evaluation_id,
                "profile_name": request.profile_name,
                "score_config_hash": request.score_config_hash,
                "profile_version_hash": request.profile_version_hash,
                "llm_config_hash": request.llm_config_hash,
                "model_name": request.model_name,
                "execution_mode": request.execution_mode,
                "prompt_template_version": request.prompt_template_version,
                "schema_version": request.schema_version,
                "provider_request_id": request.provider_request_id,
                "batch_id": request.batch_id,
                "batch_custom_id": request.batch_custom_id,
                "request_payload_json": request.request_payload_json,
                "response_payload_json": request.response_payload_json,
                "request_status": request.request_status,
                "error_type": request.error_type,
                "error_message": request.error_message,
                "retry_count": request.retry_count,
                "sent_at": request.sent_at,
                "finished_at": request.finished_at,
            }
        ]

        return self.db_manager.save_rows(
            table_name="llm_requests",
            rows=rows,
            mode=WriteMode.APPEND,
        )

    def save_usage_metrics(
        self,
        usage: LLMUsageMetricsRecord,
    ) -> int:
        """Persist token usage and estimated cost for one LLM request."""
        rows = [
            {
                "llm_request_id": usage.llm_request_id,
                "raw_job_ad_id": usage.raw_job_ad_id,
                "profile_name": usage.profile_name,
                "score_config_hash": usage.score_config_hash,
                "model_name": usage.model_name,
                "execution_mode": usage.execution_mode,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "total_tokens": usage.total_tokens,
                "cached_input_tokens": usage.cached_input_tokens,
                "estimated_input_cost_usd": usage.estimated_input_cost_usd,
                "estimated_output_cost_usd": usage.estimated_output_cost_usd,
                "estimated_total_cost_usd": usage.estimated_total_cost_usd,
            }
        ]

        return self.db_manager.save_rows(
            table_name="llm_usage_metrics",
            rows=rows,
            mode=WriteMode.APPEND,
        )

    def get_evaluations_for_profile(
        self,
        profile_name: str,
        score_config_hash: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return persisted LLM evaluations for a profile/config pair."""
        sql = """
            SELECT
                id,
                raw_job_ad_id,
                profile_name,
                score_config_hash,
                profile_version_hash,
                llm_config_hash,
                model_name,
                execution_mode,
                prompt_template_version,
                schema_version,
                job_content_hash,
                fit_score,
                fit_label,
                recommended,
                confidence,
                summary,
                fit_reasons,
                salary_mentioned,
                salary_min,
                salary_max,
                salary_currency,
                salary_period,
                salary_raw_text,
                remote_type,
                seniority,
                raw_result_json,
                request_status,
                processed_at,
                created_at,
                updated_at
            FROM llm_evaluations
            WHERE profile_name = %s
              AND score_config_hash = %s
            ORDER BY processed_at DESC, id DESC
        """

        params: list[Any] = [profile_name, score_config_hash]

        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)

        return self.db_manager.fetch_all(sql, tuple(params))
    

    def get_existing_evaluation_job_ids(
        self,
        raw_job_ad_ids: Iterable[int],
        profile_name: str,
        score_config_hash: str,
        profile_version_hash: str,
        llm_config_hash: str,
        model_name: str,
        execution_mode: str,
    ) -> set[int]:
        """
        Return the subset of raw_job_ad_ids that already have a persisted LLM
        evaluation for the given profile/config/model combination.
        """
        raw_job_ad_ids = list(raw_job_ad_ids)
        if not raw_job_ad_ids:
            return set()

        sql = """
            SELECT DISTINCT raw_job_ad_id
            FROM llm_evaluations
            WHERE raw_job_ad_id = ANY(%s)
              AND profile_name = %s
              AND score_config_hash = %s
              AND profile_version_hash = %s
              AND llm_config_hash = %s
              AND model_name = %s
              AND execution_mode = %s
        """

        rows = self.db_manager.fetch_all(
            sql,
            (
                raw_job_ad_ids,
                profile_name,
                score_config_hash,
                profile_version_hash,
                llm_config_hash,
                model_name,
                execution_mode,
            ),
        )

        return {row["raw_job_ad_id"] for row in rows}