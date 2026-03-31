CREATE TABLE IF NOT EXISTS llm_usage_metrics (
    id BIGSERIAL PRIMARY KEY,

    llm_request_id BIGINT NOT NULL REFERENCES llm_requests(id) ON DELETE CASCADE,
    raw_job_ad_id BIGINT NOT NULL REFERENCES raw_job_ads(id) ON DELETE CASCADE,

    profile_name TEXT NOT NULL,
    score_config_hash TEXT NOT NULL,

    model_name TEXT NOT NULL,
    execution_mode TEXT NOT NULL, -- standard | batch

    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    cached_input_tokens INTEGER NOT NULL DEFAULT 0,

    estimated_input_cost_usd NUMERIC(12,6),
    estimated_output_cost_usd NUMERIC(12,6),
    estimated_total_cost_usd NUMERIC(12,6),

    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_metrics_request_id
    ON llm_usage_metrics(llm_request_id);

CREATE INDEX IF NOT EXISTS idx_llm_usage_metrics_model_name
    ON llm_usage_metrics(model_name);

CREATE INDEX IF NOT EXISTS idx_llm_usage_metrics_created_at
    ON llm_usage_metrics(created_at);