ALTER TABLE renewableops.audit_events
    ADD COLUMN IF NOT EXISTS resource_version TEXT,
    ADD COLUMN IF NOT EXISTS previous_hash TEXT,
    ADD COLUMN IF NOT EXISTS event_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_events_event_hash
    ON renewableops.audit_events (event_hash)
    WHERE event_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS renewableops.dataset_lineage (
    lineage_id UUID PRIMARY KEY,
    run_id UUID,
    input_datasets JSONB NOT NULL,
    input_versions JSONB NOT NULL,
    code_commit TEXT NOT NULL,
    parameters JSONB NOT NULL,
    output_dataset TEXT NOT NULL,
    output_version TEXT NOT NULL,
    input_row_count BIGINT NOT NULL CHECK (input_row_count >= 0),
    output_row_count BIGINT NOT NULL CHECK (output_row_count >= 0),
    quality_status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NOT NULL,
    owner TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dataset_lineage_output
    ON renewableops.dataset_lineage (output_dataset, finished_at DESC);
