from typing import Any, Iterable

from src.database.db_manager import DBManager
from src.scrapers.models import WriteMode


class RawJobAdsRepository:
    def __init__(self, db_manager: DBManager) -> None:
        self.db_manager = db_manager

    def save_raw_job_ads(
        self,
        jobs: Iterable[Any],
        mode: WriteMode = WriteMode.UPSERT,
    ) -> int:
        rows = [self.db_manager._to_dict(job) for job in jobs]

        for row in rows:
            row.setdefault("metadata", {})
            row.pop("id", None)
            row.pop("created_at", None)
            row.pop("updated_at", None)

        return self.db_manager.save_rows(
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
                "last_scraped_at",
                "last_seen_at",
            ],
        )

    def get_raw_job_ads(
        self,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                id,
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
                metadata,
                first_scraped_at,
                last_scraped_at,
                last_seen_at
            FROM raw_job_ads
            ORDER BY id DESC
        """

        params: tuple[Any, ...] | None = None
        if limit is not None:
            sql += " LIMIT %s"
            params = (limit,)

        return self.db_manager.fetch_all(sql, params)

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
                r.metadata,
                r.first_scraped_at,
                r.last_scraped_at,
                r.last_seen_at
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

        return self.db_manager.fetch_all(sql, tuple(params))

    def get_known_ads_by_ids(
        self,
        source: str,
        ad_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        if not ad_ids:
            return {}

        sql = """
            SELECT
                id,
                source,
                ad_id,
                ad_link,
                title,
                company_name,
                description,
                input_location,
                job_location,
                posted_date,
                work_mode,
                metadata,
                first_scraped_at,
                last_scraped_at,
                last_seen_at
            FROM raw_job_ads
            WHERE source = %s
              AND ad_id = ANY(%s)
        """

        rows = self.db_manager.fetch_all(sql, (source, ad_ids))
        return {row["ad_id"]: row for row in rows}

    def touch_last_seen_at(
        self,
        source: str,
        ad_ids: list[str],
        seen_at,
    ) -> None:
        if not ad_ids:
            return

        sql = """
            UPDATE raw_job_ads
            SET
                last_seen_at = %s,
                updated_at = NOW()
            WHERE source = %s
              AND ad_id = ANY(%s)
        """
        self.db_manager.execute(sql, (seen_at, source, ad_ids))