import logging
import os

from src.core.logging_config import setup_logging
from src.database.db_manager import DBManager
from src.helpers.helpers import build_config_hash, build_config_json
from src.matching.job_scorer import JobScorer
from src.matching.score_config import JobScoreConfig, WeightedTerms
from src.scrapers.models import RawJobAd


def main():
    setup_logging(logging.INFO)

    dsn = os.getenv(
        "JOB_MATCHER_DSN",
        "postgresql://postgres:postgres@localhost:5432/job_matcher",
    )

    db_manager = DBManager(dsn=dsn)

    profile_name = "mihail_data_eng"

    score_config = JobScoreConfig(
        title_contains=[
            WeightedTerms(
                terms=["data engineer", "senior data engineer", "data platform engineer"],
                weight=10,
            ),
            WeightedTerms(
                terms=["data developer", "data platform engineer", "cloud platform engineer", "devops"],
                weight=6,
            ),
        ],
        body_contains=[
            WeightedTerms(
                terms=["python", "sql", "airflow", "etl", "spark", "scala", "terraform", "gcp"],
                weight=4,
            ),
            WeightedTerms(
                terms=["kafka", "aws", "azure", "github", "gitlab", "ci/cd", "ci-cd", "etl pipeline", "data pipeline", "fast api", "rest api"],
                weight=2,
            ),
        ],
        allowed_languages=["en"],
        min_score_for_selection=10,
    )

    config_hash = build_config_hash(score_config)
    config_json = build_config_json(score_config)

    db_manager.save_scoring_config(
        profile_name=profile_name,
        config_hash=config_hash,
        config_json=config_json,
    )

    raw_rows = db_manager.get_raw_job_ads_for_scoring(
        profile_name=profile_name,
        config_hash=config_hash,
        # limit=400,
    )

    jobs = [RawJobAd(**row) for row in raw_rows]

    logging.info("Loaded %s raw jobs to score", len(jobs))

    scorer = JobScorer(config=score_config)
    scored_jobs = scorer.score_jobs(jobs)

    saved_scores = db_manager.save_job_scores(
        scored_jobs=scored_jobs,
        profile_name=profile_name,
        config_hash=config_hash,
    )

    logging.info("Saved %s job scores", saved_scores)

    selected = db_manager.get_selected_job_scores_with_config(
        profile_name=profile_name,
        config_hash=config_hash,
        limit=10,
    )

    for row in selected:
        print("=" * 80)
        print(row["title"])
        print(row["company_name"])
        print(f"Score: {row['score']}")
        print(f"Location: {row['location']}")
        print(f"Config used: {row['config_json']}")


if __name__ == "__main__":
    main()