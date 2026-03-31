CREATE TABLE IF NOT EXISTS llm_evaluations (
    id BIGSERIAL PRIMARY KEY,

    raw_job_ad_id BIGINT NOT NULL REFERENCES raw_job_ads(id) ON DELETE CASCADE,

    profile_name TEXT NOT NULL,
    score_config_hash TEXT NOT NULL,
    profile_version_hash TEXT NOT NULL,
    llm_config_hash TEXT NOT NULL,

    model_name TEXT NOT NULL,
    execution_mode TEXT NOT NULL, -- standard | batch
    prompt_template_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,

    job_content_hash TEXT NOT NULL,

    fit_score INTEGER NOT NULL,
    fit_label TEXT NOT NULL, -- strong_fit | medium_fit | weak_fit | not_fit
    recommended BOOLEAN NOT NULL,
    confidence NUMERIC(5,4),

    summary TEXT NOT NULL,
    fit_reasons JSONB NOT NULL,

    salary_mentioned BOOLEAN NOT NULL DEFAULT FALSE,
    salary_min NUMERIC,
    salary_max NUMERIC,
    salary_currency TEXT,
    salary_period TEXT, -- hour | day | month | year | unknown
    salary_raw_text TEXT,

    remote_type TEXT NOT NULL, -- remote | hybrid | on_site | unknown
    seniority TEXT NOT NULL,   -- junior | mid | senior | lead | staff | principal | unknown

    raw_result_json JSONB NOT NULL,

    request_status TEXT NOT NULL DEFAULT 'completed', -- completed | failed | skipped
    processed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (
        raw_job_ad_id,
        profile_name,
        score_config_hash,
        profile_version_hash,
        llm_config_hash,
        model_name,
        execution_mode,
        job_content_hash
    )
);

CREATE INDEX IF NOT EXISTS idx_llm_evaluations_raw_job_ad_id
    ON llm_evaluations(raw_job_ad_id);

CREATE INDEX IF NOT EXISTS idx_llm_evaluations_profile_config
    ON llm_evaluations(profile_name, score_config_hash);

CREATE INDEX IF NOT EXISTS idx_llm_evaluations_processed_at
    ON llm_evaluations(processed_at);