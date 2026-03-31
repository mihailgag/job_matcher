import logging
import os

from src.core.logging_config import setup_logging
from src.database.db_manager import DBManager
from src.database.repositories.raw_job_ads_repository import RawJobAdsRepository
from src.database.repositories.scoring_repository import ScoringRepository
from src.matching.models import JobScoreConfig, WeightedTerms
from src.scrapers.models import WorkMode
from src.services.scoring_service import LLMEligibilityConfig, ScoringService


def build_mihail_score_config() -> JobScoreConfig:
    return JobScoreConfig(
        title_contains=[
            WeightedTerms(
                terms=["data engineer", "senior data engineer", "data platform engineer"],
                weight=10,
            ),
            WeightedTerms(
                terms=[
                    "data developer",
                    "data platform engineer",
                    "cloud platform engineer",
                    "gcp cloud engineer",
                    "gcp data engineer",
                ],
                weight=6,
            ),
        ],
        body_contains=[
            WeightedTerms(
                terms=[
                    "python",
                    "sql",
                    "airflow",
                    "etl",
                    "spark",
                    "scala",
                    "terraform",
                    "gcp",
                ],
                weight=4,
            ),
            WeightedTerms(
                terms=[
                    "aws",
                    "azure",
                    "github",
                    "gitlab",
                    "ci/cd",
                    "ci-cd",
                    "etl pipeline",
                    "data pipeline",
                    "fast api",
                    "rest api",
                ],
                weight=2,
            ),
        ],
        allowed_languages=["en"],
        min_score_for_selection=10,
    )


def main() -> None:
    setup_logging(logging.INFO)

    dsn = os.getenv(
        "JOB_MATCHER_DSN",
        "postgresql://postgres:postgres@localhost:5432/job_matcher",
    )

    db_manager = DBManager(dsn=dsn)

    raw_job_ads_repository = RawJobAdsRepository(db_manager)
    scoring_repository = ScoringRepository(db_manager)

    scoring_service = ScoringService(
        raw_job_ads_repository=raw_job_ads_repository,
        scoring_repository=scoring_repository,
    )

    profile_name = "mihail_data_eng"

    score_config = build_mihail_score_config()

    result = scoring_service.run(
        profile_name=profile_name,
        score_config=score_config,
        raw_jobs_limit=None,
    )

    logging.info(
        (
            "Scoring finished for profile_name='%s'. "
            "config_hash='%s', loaded_jobs=%s, saved_scores=%s, eligible_jobs=%s"
        ),
        result.profile_name,
        result.config_hash,
        result.loaded_jobs_count,
        result.saved_scores_count,
        result.eligible_jobs_count,
    )


if __name__ == "__main__":
    main()