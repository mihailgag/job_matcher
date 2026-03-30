from typing import Any

from src.database.db_manager import DBManager
from src.scrapers.models import WriteMode


class LocationMappingsRepository:
    def __init__(self, db_manager: DBManager) -> None:
        self.db_manager = db_manager

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
        return self.db_manager.fetch_all(sql, (source, input_location, input_location))

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

        return self.db_manager.save_rows(
            table_name="location_mappings",
            rows=rows,
            mode=WriteMode.UPSERT,
            conflict_columns=["source", "input_location", "geo_id"],
            update_columns=["resolved_location", "country", "region"],
        )