from datetime import datetime
from typing import Any, Protocol


class RawJobAdsRepositoryProtocol(Protocol):
    def save_raw_job_ads(self, jobs, mode=None) -> int:
        ...

    def get_known_ads_by_ids(
        self,
        source: str,
        ad_ids: list[str],
    ) -> dict[str, dict[str, Any]]:
        ...

    def touch_last_seen_at(
        self,
        source: str,
        ad_ids: list[str],
        seen_at: datetime,
    ) -> None:
        ...


class LocationMappingsRepositoryProtocol(Protocol):
    def get_location_mappings(
        self,
        source: str,
        input_location: str,
    ) -> list[dict[str, Any]]:
        ...

    def save_location_mappings(
        self,
        source: str,
        input_location: str,
        mappings: list[dict[str, Any]],
    ) -> int:
        ...