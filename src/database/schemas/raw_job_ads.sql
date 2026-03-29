CREATE TABLE IF NOT EXISTS raw_job_ads (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    ad_id TEXT NOT NULL,
    ad_link TEXT NOT NULL,
    title TEXT,
    company_name TEXT,
    input_location TEXT,
    job_location TEXT,
    posted_date DATE,
    work_mode TEXT,
    description TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_scraped_at TIMESTAMPTZ,
    last_scraped_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    CONSTRAINT uq_raw_job_ads_source_ad_id UNIQUE (source, ad_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_job_ads_source
    ON raw_job_ads (source);

CREATE INDEX IF NOT EXISTS idx_raw_job_ads_company_name
    ON raw_job_ads (company_name);

CREATE INDEX IF NOT EXISTS idx_raw_job_ads_metadata_gin
    ON raw_job_ads
    USING GIN (metadata);