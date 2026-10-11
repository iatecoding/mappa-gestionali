PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS registry_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_cache (
    canonical_url TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('ready', 'failed', 'blocked', 'not_found')),
    last_fetch_at TEXT,
    refresh_after TEXT,
    http_status INTEGER,
    content_type TEXT,
    byte_size INTEGER,
    content_hash TEXT,
    etag TEXT,
    last_modified TEXT,
    retention TEXT CHECK (retention IN ('metadata', 'excerpt', 'artifact')),
    rights_basis TEXT,
    artifact_path TEXT,
    extract_path TEXT,
    source_id INTEGER,
    notes TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS source_cache_refresh_idx ON source_cache(refresh_after);

CREATE TABLE IF NOT EXISTS research_leases (
    target_key TEXT PRIMARY KEY,
    target_kind TEXT NOT NULL CHECK (target_kind IN ('url', 'candidate')),
    canonical_url TEXT,
    display_name TEXT,
    agent_id TEXT NOT NULL,
    purpose TEXT NOT NULL,
    leased_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS research_leases_expiry_idx ON research_leases(expires_at);

CREATE TABLE IF NOT EXISTS discovery_candidates (
    candidate_key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    company_name TEXT,
    vat_id TEXT,
    website TEXT,
    discovery_source_url TEXT,
    discovery_method TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'researching', 'qualified', 'rejected', 'duplicate')),
    priority INTEGER NOT NULL DEFAULT 50 CHECK (priority BETWEEN 0 AND 100),
    duplicate_of TEXT REFERENCES discovery_candidates(candidate_key),
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS discovery_candidates_vat_unique ON discovery_candidates(vat_id) WHERE vat_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS discovery_candidates_status_priority_idx ON discovery_candidates(status, priority DESC);
