PRAGMA foreign_keys = ON;

CREATE TABLE schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE imports (
    record_id TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    source_path TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    importer_version TEXT NOT NULL,
    supersedes_record_id TEXT
);

CREATE TABLE company_groups (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    legal_name TEXT,
    website TEXT,
    headquarters_country TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX company_groups_name_idx ON company_groups(name COLLATE NOCASE);

CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    legal_name TEXT,
    vat_id TEXT,
    website TEXT,
    headquarters_city TEXT,
    headquarters_region TEXT,
    headquarters_country TEXT NOT NULL DEFAULT 'IT',
    founded_year INTEGER CHECK (founded_year IS NULL OR founded_year BETWEEN 1800 AND 2100),
    employee_band TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX companies_vat_unique ON companies(vat_id) WHERE vat_id IS NOT NULL;
CREATE INDEX companies_name_idx ON companies(name COLLATE NOCASE);

CREATE TABLE company_group_memberships (
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES company_groups(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL DEFAULT 'member' CHECK (relationship_type IN ('member', 'parent', 'subsidiary', 'brand')),
    source_id INTEGER REFERENCES sources(id),
    evidence_excerpt TEXT,
    PRIMARY KEY (company_id, group_id)
);

CREATE INDEX company_group_memberships_group_idx ON company_group_memberships(group_id, company_id);

CREATE TABLE industry_codes (
    id INTEGER PRIMARY KEY,
    classification_system TEXT NOT NULL DEFAULT 'ATECO',
    classification_version TEXT NOT NULL,
    code TEXT NOT NULL,
    label TEXT,
    parent_code TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    UNIQUE(classification_system, classification_version, code)
);

CREATE TABLE company_industry_codes (
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    industry_code_id INTEGER NOT NULL REFERENCES industry_codes(id),
    role TEXT NOT NULL CHECK (role IN ('primary', 'secondary')),
    valid_from TEXT,
    valid_to TEXT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    evidence_excerpt TEXT,
    PRIMARY KEY (company_id, industry_code_id)
);

CREATE INDEX company_industry_codes_code_idx ON company_industry_codes(industry_code_id, company_id);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    website TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'legacy', 'discontinued', 'unknown')),
    deployment TEXT,
    description TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(company_id, slug)
);

CREATE INDEX products_company_idx ON products(company_id);
CREATE INDEX products_name_idx ON products(name COLLATE NOCASE);

CREATE TABLE taxonomy_terms (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('category', 'vertical', 'segment', 'deployment', 'pricing_model')),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    parent_id INTEGER REFERENCES taxonomy_terms(id),
    description TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    UNIQUE(kind, slug)
);

CREATE TABLE product_terms (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    term_id INTEGER NOT NULL REFERENCES taxonomy_terms(id),
    relevance REAL NOT NULL DEFAULT 1.0 CHECK (relevance BETWEEN 0 AND 1),
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    source_id INTEGER REFERENCES sources(id),
    evidence_excerpt TEXT,
    PRIMARY KEY (product_id, term_id)
);

CREATE INDEX product_terms_term_idx ON product_terms(term_id, product_id);

CREATE TABLE features (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    feature_group TEXT,
    description TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json))
);

CREATE TABLE product_features (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    feature_id INTEGER NOT NULL REFERENCES features(id),
    support_level TEXT NOT NULL CHECK (support_level IN ('native', 'addon', 'integration', 'planned', 'unknown')),
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    source_id INTEGER REFERENCES sources(id),
    evidence_excerpt TEXT,
    PRIMARY KEY (product_id, feature_id)
);

CREATE INDEX product_features_feature_idx ON product_features(feature_id, product_id);

CREATE TABLE technical_terms (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN (
        'deployment_model', 'delivery_model', 'client_platform', 'mobile_platform',
        'api_protocol', 'integration_standard', 'database', 'programming_language',
        'framework', 'cloud_provider', 'hosting_model', 'authentication',
        'security_standard', 'data_residency', 'extensibility', 'hardware_integration', 'auditability'
    )),
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    UNIQUE(kind, slug)
);

CREATE TABLE product_technical_terms (
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    technical_term_id INTEGER NOT NULL REFERENCES technical_terms(id),
    relationship_type TEXT NOT NULL CHECK (relationship_type IN ('supports', 'uses', 'compatible_with', 'certified_for', 'available_as', 'unknown')),
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    source_id INTEGER REFERENCES sources(id),
    evidence_excerpt TEXT,
    PRIMARY KEY (product_id, technical_term_id)
);

CREATE INDEX product_technical_terms_term_idx ON product_technical_terms(technical_term_id, product_id);

CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    canonical_url TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'official_product_page', 'official_company_page', 'official_pricing_page',
        'annual_report', 'company_register', 'press_release', 'news_article',
        'review_platform', 'directory', 'other'
    )),
    publisher TEXT,
    title TEXT,
    published_at TEXT,
    accessed_at TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'it',
    content_hash TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json))
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL UNIQUE REFERENCES sources(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL DEFAULT 'web_page',
    title TEXT,
    extracted_text TEXT NOT NULL,
    extraction_method TEXT,
    storage_path TEXT,
    metadata_json TEXT CHECK (metadata_json IS NULL OR json_valid(metadata_json)),
    created_at TEXT NOT NULL
);

CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    heading TEXT,
    text TEXT NOT NULL,
    char_start INTEGER,
    char_end INTEGER,
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX chunks_document_idx ON document_chunks(document_id, chunk_index);

CREATE VIRTUAL TABLE document_chunks_fts USING fts5(
    heading,
    text,
    content='document_chunks',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER document_chunks_ai AFTER INSERT ON document_chunks BEGIN
    INSERT INTO document_chunks_fts(rowid, heading, text)
    VALUES (new.id, new.heading, new.text);
END;
CREATE TRIGGER document_chunks_ad AFTER DELETE ON document_chunks BEGIN
    INSERT INTO document_chunks_fts(document_chunks_fts, rowid, heading, text)
    VALUES ('delete', old.id, old.heading, old.text);
END;
CREATE TRIGGER document_chunks_au AFTER UPDATE ON document_chunks BEGIN
    INSERT INTO document_chunks_fts(document_chunks_fts, rowid, heading, text)
    VALUES ('delete', old.id, old.heading, old.text);
    INSERT INTO document_chunks_fts(rowid, heading, text)
    VALUES (new.id, new.heading, new.text);
END;

CREATE TABLE financial_metrics (
    id INTEGER PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('company', 'product', 'group')),
    subject_id INTEGER NOT NULL,
    metric TEXT NOT NULL CHECK (metric IN ('revenue', 'ebitda', 'net_income', 'employees', 'customers')),
    period_year INTEGER NOT NULL CHECK (period_year BETWEEN 1800 AND 2100),
    value_exact REAL,
    value_min REAL,
    value_max REAL,
    currency TEXT,
    value_kind TEXT NOT NULL CHECK (value_kind IN ('reported', 'estimated', 'derived')),
    methodology TEXT,
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    source_id INTEGER NOT NULL REFERENCES sources(id),
    evidence_excerpt TEXT,
    CHECK (value_exact IS NOT NULL OR value_min IS NOT NULL OR value_max IS NOT NULL)
);

CREATE INDEX financial_subject_metric_year_idx
    ON financial_metrics(subject_type, subject_id, metric, period_year DESC);

CREATE TABLE facts (
    id INTEGER PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('company', 'product', 'group')),
    subject_id INTEGER NOT NULL,
    predicate TEXT NOT NULL,
    value_text TEXT,
    value_number REAL,
    value_boolean INTEGER CHECK (value_boolean IN (0, 1)),
    value_json TEXT CHECK (value_json IS NULL OR json_valid(value_json)),
    unit TEXT,
    valid_from TEXT,
    valid_to TEXT,
    value_kind TEXT NOT NULL CHECK (value_kind IN ('reported', 'estimated', 'derived', 'observed')),
    methodology TEXT,
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    source_id INTEGER NOT NULL REFERENCES sources(id),
    evidence_excerpt TEXT,
    CHECK (value_text IS NOT NULL OR value_number IS NOT NULL OR value_boolean IS NOT NULL OR value_json IS NOT NULL)
);

CREATE INDEX facts_subject_predicate_idx ON facts(subject_type, subject_id, predicate);
CREATE INDEX facts_predicate_number_idx ON facts(predicate, value_number) WHERE value_number IS NOT NULL;

CREATE TABLE claims (
    id INTEGER PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('company', 'product', 'group')),
    subject_id INTEGER NOT NULL,
    claim_type TEXT NOT NULL CHECK (claim_type IN ('observed', 'inferred', 'estimated')),
    predicate TEXT NOT NULL,
    statement TEXT NOT NULL,
    assessment TEXT,
    methodology TEXT,
    confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
    source_id INTEGER NOT NULL REFERENCES sources(id),
    evidence_excerpt TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX claims_subject_predicate_idx ON claims(subject_type, subject_id, predicate);

CREATE TABLE notes (
    id INTEGER PRIMARY KEY,
    subject_type TEXT NOT NULL CHECK (subject_type IN ('company', 'product', 'group')),
    subject_id INTEGER NOT NULL,
    note_type TEXT NOT NULL CHECK (note_type IN (
        'analyst_inference', 'research_note', 'data_quality', 'source_quality', 'classification_rationale'
    )),
    text TEXT NOT NULL,
    confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX notes_subject_idx ON notes(subject_type, subject_id);

CREATE VIEW v_product_overview AS
SELECT
    p.id AS product_id,
    p.name AS product_name,
    p.slug AS product_slug,
    p.website AS product_website,
    p.status,
    p.deployment,
    c.id AS company_id,
    c.name AS company_name,
    c.headquarters_region,
    c.employee_band
FROM products p
JOIN companies c ON c.id = p.company_id;

CREATE VIEW v_product_feature_matrix AS
SELECT
    p.id AS product_id,
    p.name AS product_name,
    f.id AS feature_id,
    f.slug AS feature_slug,
    f.name AS feature_name,
    pf.support_level,
    pf.confidence
FROM product_features pf
JOIN products p ON p.id = pf.product_id
JOIN features f ON f.id = pf.feature_id;

CREATE VIEW v_latest_company_revenue AS
SELECT fm.*
FROM financial_metrics fm
WHERE fm.subject_type = 'company'
  AND fm.metric = 'revenue'
  AND fm.period_year = (
      SELECT MAX(other.period_year)
      FROM financial_metrics other
      WHERE other.subject_type = fm.subject_type
        AND other.subject_id = fm.subject_id
        AND other.metric = fm.metric
  );

CREATE VIEW v_product_technical_matrix AS
SELECT
    p.id AS product_id,
    p.name AS product_name,
    t.kind AS technical_kind,
    t.slug AS technical_slug,
    t.name AS technical_name,
    pt.relationship_type,
    pt.confidence
FROM product_technical_terms pt
JOIN products p ON p.id = pt.product_id
JOIN technical_terms t ON t.id = pt.technical_term_id;

CREATE VIEW v_company_primary_ateco AS
SELECT
    c.id AS company_id,
    c.name AS company_name,
    c.vat_id,
    code.classification_version,
    code.code AS ateco_code,
    code.label AS ateco_label,
    membership.valid_from,
    membership.valid_to
FROM company_industry_codes membership
JOIN companies c ON c.id = membership.company_id
JOIN industry_codes code ON code.id = membership.industry_code_id
WHERE membership.role = 'primary'
  AND code.classification_system = 'ATECO';
