from typing import Any, Iterable

from src.helpers.helpers import detect_language
from src.matching.score_config import (
    JobScoreConfig,
    JobScoreResult,
    WeightedTerms,
)
from src.scrapers.models import RawJobAd


class JobScorer:
    def __init__(self, config: JobScoreConfig) -> None:
        self.config = config

    def score_job(self, job: RawJobAd) -> JobScoreResult:
        title = (job.title or "").lower()
        body = " ".join(
            [
                job.title or "",
                job.company_name or "",
                job.company_info or "",
                job.description or "",
            ]
        ).lower()

        detected_language = detect_language(body)

        if detected_language not in self.config.allowed_languages:
            return JobScoreResult(
                score=0,
                selected=False,
                detected_language=detected_language,
                rejection_reason="language_not_allowed",
                reasons={
                    "allowed_languages": self.config.allowed_languages,
                    "detected_language": detected_language,
                },
            )

        score = 0
        reasons: dict[str, Any] = {
            "detected_language": detected_language,
            "title_contains": [],
            "body_contains": [],
        }

        score += self._apply_terms(
            text=title,
            weighted_terms=self.config.title_contains,
            bucket=reasons["title_contains"],
        )
        score += self._apply_terms(
            text=body,
            weighted_terms=self.config.body_contains,
            bucket=reasons["body_contains"],
        )

        return JobScoreResult(
            score=score,
            selected=score >= self.config.min_score_for_selection,
            detected_language=detected_language,
            reasons=reasons,
        )

    def score_jobs(
        self,
        jobs: Iterable[RawJobAd],
    ) -> list[tuple[RawJobAd, JobScoreResult]]:
        return [(job, self.score_job(job)) for job in jobs]

    @staticmethod
    def _apply_terms(
        text: str,
        weighted_terms: list[WeightedTerms],
        bucket: list[dict[str, Any]],
    ) -> int:
        delta = 0

        for group in weighted_terms:
            matched_terms = [term for term in group.terms if term.lower() in text]
            if not matched_terms:
                continue

            delta += group.weight
            bucket.append(
                {
                    "matched_terms": matched_terms,
                    "weight": group.weight,
                }
            )

        return delta