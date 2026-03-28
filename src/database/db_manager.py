import json
import logging
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Literal
from dataclasses import asdict

import psycopg
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier, Placeholder

from src.matching.score_config import JobScoreResult
from src.scrapers.models import RawJobAd


WriteMode = Literal["append", "upsert"]


class DBManager:
    def __init__(self, dsn: str, schema_dir: str = "src/database/schemas") -> None:
        self.dsn = dsn
        self.schema_dir = Path(schema_dir)
        self.create_table_from_sql_file("raw_job_ads.sql")
        self.create_table_from_sql_file("linkedin_location_mappings.sql")
        self.create_table_from_sql_file("job_scores.sql")
        self.create_table_from_sql_file("input_scoring_configs.sql")
 
    @contextmanager
    def get_connection(self):
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def execute(self, sql: str, params: tuple | None = None) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

    def fetch_all(
        self,
        sql: str,
        params: tuple | None = None,
    ) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())

    def create_table_from_sql_file(self, file_name: str) -> None:
        file_path = self.schema_dir / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")

        sql_text = file_path.read_text(encoding="utf-8")

        logging.info("Ensuring table from schema file: %s", file_path)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)

    def save_rows(
        self,
        table_name: str,
        rows: Iterable[dict[str, Any]],
        mode: WriteMode = "upsert",
        conflict_columns: list[str] | None = None,
        update_columns: list[str] | None = None,
    ) -> int:
        rows = list(rows)
        if not rows:
            logging.info("No rows received for table '%s'.", table_name)
            return 0

        normalized_rows = [self._normalize_row(row) for row in rows]

        columns = list(normalized_rows[0].keys())

        for row in normalized_rows:
            missing = set(columns) - set(row.keys())
            extra = set(row.keys()) - set(columns)
            if missing or extra:
                raise ValueError(
                    f"All rows must have the same keys. Missing={missing}, extra={extra}"
                )

        values = [tuple(row[col] for col in columns) for row in normalized_rows]

        insert_sql = self._build_insert_sql(
            table_name=table_name,
            columns=columns,
            mode=mode,
            conflict_columns=conflict_columns,
            update_columns=update_columns,
        )

        logging.info(
            "Writing %s rows to table '%s' using mode='%s'.",
            len(values),
            table_name,
            mode,
        )

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(insert_sql, values)

        return len(values)

    def save_raw_job_ads(
        self,
        jobs: Iterable[Any],
        mode: WriteMode = "upsert",
    ) -> int:
        rows = [self._to_dict(job) for job in jobs]

        for row in rows:
            row.setdefault("metadata", {})
            row.pop("id", None)
            row.pop("created_at", None)
            row.pop("updated_at", None)

        return self.save_rows(
            table_name="raw_job_ads",
            rows=rows,
            mode=mode,
            conflict_columns=["source", "ad_id"],
            update_columns=[
                "ad_link",
                "title",
                "company_name",
                "input_location",
                "job_location",
                "posted_date",
                "work_mode",
                "description",
                "metadata",
            ],
        )
    
    def get_raw_job_ads(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                source,
                ad_id,
                ad_link,
                title,
                company_name,
                input_location,
                job_location,
                work_mode,
                posted_date,
                description,
                metadata
            FROM raw_job_ads
            ORDER BY id DESC
        """

        params: tuple[Any, ...] | None = None

        if limit is not None:
            sql += " LIMIT %s"
            params = (limit,)

        return self.fetch_all(sql, params)
    

    def get_raw_job_ads_for_scoring(
        self,
        profile_name: str,
        config_hash: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                r.id,
                r.source,
                r.ad_id,
                r.ad_link,
                r.title,
                r.company_name,
                r.input_location,
                r.job_location,
                r.work_mode,
                r.posted_date,
                r.description,
                r.metadata
            FROM raw_job_ads r
            WHERE NOT EXISTS (
                SELECT 1
                FROM job_scores s
                WHERE s.raw_job_ad_id = r.id
                AND s.profile_name = %s
                AND s.config_hash = %s
            )
            ORDER BY r.id DESC
        """

        params: list[Any] = [profile_name, config_hash]

        if limit is not None:
            sql += " LIMIT %s"
            params.append(limit)

        return self.fetch_all(sql, tuple(params))
    
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

        return self.save_rows(
            table_name="job_scores",
            rows=rows,
            mode="upsert",
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

        return self.save_rows(
            table_name="scoring_configs",
            rows=rows,
            mode="upsert",
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
        return self.fetch_all(sql, (profile_name, config_hash))
    
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

        return self.fetch_all(sql, tuple(params))

    @staticmethod
    def _to_dict(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return dict(item)
        if is_dataclass(item):
            return asdict(item)
        raise TypeError(f"Unsupported row type: {type(item)!r}")

    @staticmethod
    def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, dict):
                normalized[key] = json.dumps(value)
            else:
                normalized[key] = value
        return normalized

    def _build_insert_sql(
        self,
        table_name: str,
        columns: list[str],
        mode: WriteMode,
        conflict_columns: list[str] | None,
        update_columns: list[str] | None,
    ):
        base_sql = SQL("INSERT INTO {table} ({cols}) VALUES ({vals})").format(
            table=Identifier(table_name),
            cols=SQL(", ").join(Identifier(col) for col in columns),
            vals=SQL(", ").join(Placeholder() for _ in columns),
        )

        if mode == "append":
            if conflict_columns:
                return base_sql + SQL(" ON CONFLICT ({conf_cols}) DO NOTHING").format(
                    conf_cols=SQL(", ").join(
                        Identifier(col) for col in conflict_columns
                    )
                )
            return base_sql

        if mode == "upsert":
            if not conflict_columns:
                raise ValueError("conflict_columns are required for upsert mode")

            if not update_columns:
                update_columns = [
                    col for col in columns if col not in set(conflict_columns)
                ]

            assignments = [
                SQL("{col} = EXCLUDED.{col}").format(col=Identifier(col))
                for col in update_columns
            ]

            if "updated_at" in columns:
                assignments.append(SQL("updated_at = NOW()"))

            return (
                base_sql
                + SQL(" ON CONFLICT ({conf_cols}) DO UPDATE SET ").format(
                    conf_cols=SQL(", ").join(
                        Identifier(col) for col in conflict_columns
                    )
                )
                + SQL(", ").join(assignments)
            )

        raise ValueError(f"Unsupported mode: {mode}")
    

    def get_location_mappings(
        self,
        source: str,
        input_location: str,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                source,
                input_location,
                resolved_location,
                geo_id,
                country,
                region
            FROM location_mappings
            WHERE source = %s
            AND LOWER(input_location) = LOWER(%s) 
            AND LOWER(resolved_location) = LOWER(%s)
            ORDER BY resolved_location;
        """
        #TODO Remove the resolved_location = %s, once tested with contries only.
        return self.fetch_all(sql, (source, input_location, input_location))
    
    def save_location_mappings(
        self,
        source: str,
        input_location: str,
        mappings: list[dict[str, Any]],
    ) -> int:
        if not mappings:
            return 0

        rows = []
        for item in mappings:
            rows.append(
                {
                    "source": source,
                    "input_location": input_location,
                    "resolved_location": item["resolved_location"],
                    "geo_id": item["geo_id"],
                    "country": item.get("country"),
                    "region": item.get("region"),
                }
            )

        return self.save_rows(
            table_name="location_mappings",
            rows=rows,
            mode="upsert",
            conflict_columns=["source", "input_location", "geo_id"],
            update_columns=["resolved_location", "country", "region"],
        )
    