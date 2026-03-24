CREATE TABLE IF NOT EXISTS location_mappings (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    input_location TEXT NOT NULL,
    resolved_location TEXT NOT NULL,
    geo_id TEXT NOT NULL,
    country TEXT,
    region TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_location_mappings UNIQUE (source, input_location, geo_id)
);

CREATE INDEX IF NOT EXISTS idx_location_mappings_source_input
    ON location_mappings (source, input_location);

CREATE INDEX IF NOT EXISTS idx_location_mappings_geo_id
    ON location_mappings (geo_id);