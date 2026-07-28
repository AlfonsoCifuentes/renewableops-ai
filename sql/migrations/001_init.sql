CREATE SCHEMA IF NOT EXISTS renewableops;

CREATE TABLE IF NOT EXISTS renewableops.assets (
    asset_id TEXT PRIMARY KEY,
    asset_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('solar', 'wind', 'battery')),
    status TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    region TEXT NOT NULL,
    municipality TEXT,
    installed_capacity_mw DOUBLE PRECISION NOT NULL CHECK (installed_capacity_mw > 0),
    commissioning_date DATE,
    timezone TEXT NOT NULL DEFAULT 'Europe/Madrid',
    manufacturer TEXT,
    model TEXT,
    portfolio_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS renewableops.pipeline_runs (
    run_id UUID PRIMARY KEY,
    pipeline_name TEXT NOT NULL,
    correlation_id UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'success', 'failed', 'cancelled')),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    input_manifest JSONB NOT NULL DEFAULT '{}',
    output_manifest JSONB NOT NULL DEFAULT '{}',
    error_redacted JSONB
);

CREATE TABLE IF NOT EXISTS renewableops.model_approvals (
    approval_id UUID PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'held')),
    approver TEXT NOT NULL,
    rationale TEXT NOT NULL,
    gates JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (model_name, model_version, approver)
);

CREATE TABLE IF NOT EXISTS renewableops.audit_events (
    event_id UUID PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    result TEXT NOT NULL,
    correlation_id UUID,
    evidence JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at
    ON renewableops.pipeline_runs (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource
    ON renewableops.audit_events (resource_type, resource_id, occurred_at DESC);
