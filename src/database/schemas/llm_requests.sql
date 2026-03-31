CREATE TABLE IF NOT EXISTS llm_requests (
    id BIGSERIAL PRIMARY KEY,

    raw_job_ad_id BIGINT NOT NULL REFERENCES raw_job_ads(id) ON DELETE CASCADE,
    llm_evaluation_id BIGINT REFERENCES llm_evaluations(id) ON DELETE SET NULL,

    profile_name TEXT NOT NULL,
    score_config_hash TEXT NOT NULL,
    profile_version_hash TEXT NOT NULL,
    llm_config_hash TEXT NOT NULL,

    model_name TEXT NOT NULL,
    execution_mode TEXT NOT NULL, -- standard | batch
    prompt_template_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,

    provider_request_id TEXT,
    batch_id TEXT,
    batch_custom_id TEXT,

    request_payload_json JSONB,
    response_payload_json JSONB,

    request_status TEXT NOT NULL, -- queued | submitted | completed | failed
    error_type TEXT,
    error_message TEXT,

    retry_count INTEGER NOT NULL DEFAULT 0,

    sent_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_requests_raw_job_ad_id
    ON llm_requests(raw_job_ad_id);

CREATE INDEX IF NOT EXISTS idx_llm_requests_status
    ON llm_requests(request_status);

CREATE INDEX IF NOT EXISTS idx_llm_requests_batch_id
    ON llm_requests(batch_id);