from typing import Any, Iterable

from src.database.db_manager import DBManager
from src.llm.models import EligibleJobLLM
from src.matching.models import JobScoreResult
from src.scrapers.models import RawJobAd, WriteMode


class ScoringRepository:
    def __init__(self, db_manager: DBManager) -> None:
        self.db_manager = db_manager

    def save_job_scores(
        self,
        scored_jobs: Iterable[tuple[RawJobAd, JobScoreResult]],
        profile_name: str,
        config_hash: str,
    ) -> int:
        rows = []

        for job, result in scored_jobs:
            if job.id is None:
                raise ValueError("RawJobAd.id is required to save scores")

            rows.append(
                {
                    "raw_job_ad_id": job.id,
                    "profile_name": profile_name,
                    "config_hash": config_hash,
                    "score": result.score,
                    "selected": result.selected,
                    "detected_language": result.detected_language,
                    "rejection_reason": result.rejection_reason,
                    "reasons": result.reasons,
                }
            )

        return self.db_manager.save_rows(
            table_name="job_scores",
            rows=rows,
            mode=WriteMode.UPSERT,
            conflict_columns=["raw_job_ad_id", "profile_name", "config_hash"],
            update_columns=[
                "score",
                "selected",
                "detected_language",
                "rejection_reason",
                "reasons",
            ],
        )

    def save_scoring_config(
        self,
        profile_name: str,
        config_hash: str,
        config_json: dict[str, Any],
    ) -> int:
        rows = [
            {
                "profile_name": profile_name,
                "config_hash": config_hash,
                "config_json": config_json,
            }
        ]

        return self.db_manager.save_rows(
            table_name="scoring_configs",
            rows=rows,
            mode=WriteMode.UPSERT,
            conflict_columns=["profile_name", "config_hash"],
            update_columns=["config_json"],
        )

    def get_scoring_config(
        self,
        profile_name: str,
        config_hash: str,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                id,
                profile_name,
                config_hash,
                config_json,
                created_at
            FROM scoring_configs
            WHERE profile_name = %s
              AND config_hash = %s
        """
        return self.db_manager.fetch_all(sql, (profile_name, config_hash))

    def get_selected_job_scores_with_config(
        self,
        profile_name: str,
        config_hash: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                s.raw_job_ad_id,
                s.profile_name,
                s.config_hash,
                s.score,
                s.selected,
                s.detected_language,
                s.rejection_reason,
                s.reasons,
                s.scored_at,
                r.title,
                r.company_name,
                r.input_location,
                r.job_location,
                r.work_mode,
                r.posted_date,
                r.ad_link,
                c.config_json
            FROM job_scores s
            INNER JOIN raw_job_ads r
                ON r.id = s.raw_job_ad_id
            INNER JOIN scoring_configs c
                ON c.profile_name = s.profile_name
               AND c.config_hash = s.config_hash
            WHERE s.profile_name = %s
              AND s.config_hash = %s
              AND s.selected = TRUE
            ORDER BY s.score DESC, s.scored_at DESC
        """

        params: list[Any] = [profile_name, config_hash]
        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)

        return self.db_manager.fetch_all(sql, tuple(params))

    def get_eligible_jobs_for_llm(
        self,
        profile_name: str,
        config_hash: str,
        min_score: int,
        max_age_days: int | None = None,
        allowed_work_modes: list[str] | None = None,
        max_description_chars: int = 3000,
        preferred_countries: list[str] | None = None,
        limit: int | None = None,
    ) -> list[EligibleJobLLM]:
        query = """
            SELECT
                s.raw_job_ad_id,
                s.score,
                r.title,
                r.company_name,
                r.job_location,
                r.work_mode,
                r.ad_link,
                r.posted_date,
                LEFT(COALESCE(r.description, ''), %(max_description_chars)s) AS description
            FROM job_scores s
            INNER JOIN raw_job_ads r
                ON r.id = s.raw_job_ad_id
            WHERE s.profile_name = %(profile_name)s
              AND s.config_hash = %(config_hash)s
              AND s.score >= %(min_score)s
              AND s.selected = TRUE
        """

        params: dict[str, object] = {
            "profile_name": profile_name,
            "config_hash": config_hash,
            "min_score": min_score,
            "max_description_chars": max_description_chars,
        }

        if max_age_days is not None:
            query += """
              AND r.posted_date IS NOT NULL
              AND r.posted_date >= CURRENT_DATE - (%(max_age_days)s * INTERVAL '1 day')
            """
            params["max_age_days"] = max_age_days

        if allowed_work_modes:
            query += """
              AND r.work_mode = ANY(%(allowed_work_modes)s)
            """
            params["allowed_work_modes"] = allowed_work_modes

        if preferred_countries:
            country_conditions = []
            for idx, country in enumerate(preferred_countries):
                param_name = f"country_{idx}"
                country_conditions.append(f"r.job_location ILIKE %({param_name})s")
                params[param_name] = f"%{country}%"

            query += f"""
              AND (
                  {" OR ".join(country_conditions)}
              )
            """

        query += """
            ORDER BY
                CASE r.work_mode
                    WHEN 'remote' THEN 1
                    WHEN 'hybrid' THEN 2
                    WHEN 'on_site' THEN 3
                    ELSE 4
                END,
                s.score DESC,
                r.posted_date DESC NULLS LAST,
                s.raw_job_ad_id
        """

        if limit is not None:
            query += "\nLIMIT %(limit)s"
            params["limit"] = limit

        rows = self.db_manager.fetch_all(query, params)

        return [
            EligibleJobLLM(
                raw_job_ad_id=row["raw_job_ad_id"],
                score=row["score"],
                title=row["title"],
                company_name=row["company_name"],
                job_location=row["job_location"],
                work_mode=row["work_mode"],
                ad_link=row["ad_link"],
                posted_date=row["posted_date"],
                description=row["description"],
            )
            for row in rows
        ]