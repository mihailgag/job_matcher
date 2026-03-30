import json
import logging
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg.rows import dict_row
from psycopg.sql import SQL, Identifier, Placeholder

from src.scrapers.models import WriteMode


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

    def execute(self, sql: str, params: tuple | dict | None = None) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)

    def fetch_all(
        self,
        sql: str,
        params: tuple | dict | None = None,
    ) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return [dict(row) for row in cur.fetchall()]

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
        mode: WriteMode = WriteMode.UPSERT,
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

        if mode == WriteMode.APPEND:
            if conflict_columns:
                return base_sql + SQL(" ON CONFLICT ({conf_cols}) DO NOTHING").format(
                    conf_cols=SQL(", ").join(Identifier(col) for col in conflict_columns)
                )
            return base_sql

        if mode == WriteMode.UPSERT:
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

            if "updated_at" in columns and "updated_at" not in update_columns:
                assignments.append(SQL("updated_at = NOW()"))

            return (
                base_sql
                + SQL(" ON CONFLICT ({conf_cols}) DO UPDATE SET ").format(
                    conf_cols=SQL(", ").join(Identifier(col) for col in conflict_columns)
                )
                + SQL(", ").join(assignments)
            )

        raise ValueError(f"Unsupported mode: {mode}")