CREATE TABLE IF NOT EXISTS job_scores (
    id BIGSERIAL PRIMARY KEY,
    raw_job_ad_id BIGINT NOT NULL REFERENCES raw_job_ads(id) ON DELETE CASCADE,
    profile_name TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    score INTEGER NOT NULL,
    selected BOOLEAN NOT NULL,
    detected_language TEXT,
    rejection_reason TEXT,
    reasons JSONB NOT NULL DEFAULT '{}'::jsonb,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_job_scores UNIQUE (raw_job_ad_id, profile_name, config_hash)
);

CREATE INDEX IF NOT EXISTS idx_job_scores_profile_hash
    ON job_scores (profile_name, config_hash);

CREATE INDEX IF NOT EXISTS idx_job_scores_raw_job_ad_id
    ON job_scores (raw_job_ad_id);

CREATE INDEX IF NOT EXISTS idx_job_scores_selected
    ON job_scores (selected);