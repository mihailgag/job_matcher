CREATE TABLE IF NOT EXISTS scoring_configs (
    id BIGSERIAL PRIMARY KEY,
    profile_name TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    config_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_scoring_configs UNIQUE (profile_name, config_hash)
);

CREATE INDEX IF NOT EXISTS idx_scoring_configs_profile_hash
    ON scoring_configs (profile_name, config_hash);