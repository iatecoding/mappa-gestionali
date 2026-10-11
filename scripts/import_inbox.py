#!/usr/bin/env python3
"""Validate and serially import research bundles into the SQLite catalogue."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from catalog_lib import (
    BundleError,
    bundle_hash,
    canonical_json,
    load_bundle,
    paths_from_input,
    slugify,
    validate_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
IMPORTER_VERSION = "1.0"


def json_value(value: Any) -> str | None:
    return canonical_json(value) if value is not None else None


def scalar_value(value: Any) -> tuple[str | None, float | None, int | None, str | None]:
    if isinstance(value, bool):
        return None, None, int(value), None
    if isinstance(value, (int, float)):
        return None, float(value), None, None
    if isinstance(value, str):
        return value, None, None, None
    return None, None, None, json_value(value)


def chunk_text(text: str, size: int = 1200) -> list[tuple[int, int, str]]:
    """Split text on paragraph/word boundaries without losing its offsets."""
    chunks: list[tuple[int, int, str]] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + size, length)
        if end < length:
            boundary = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
            if boundary > start + size // 2:
                end = boundary
        part = text[start:end].strip()
        if part:
            actual_start = text.find(part, start, end)
            chunks.append((actual_start, actual_start + len(part), part))
        start = max(end, start + 1)
    return chunks


def find_row_id(connection: sqlite3.Connection, table: str, where: str, params: tuple[Any, ...]) -> int | None:
    row = connection.execute(f"SELECT id FROM {table} WHERE {where}", params).fetchone()
    return int(row[0]) if row else None


def company_from_unique_product_website(connection: sqlite3.Connection, website: str | None) -> int | None:
    """Resolve a brand-only company only when its product URL has one owner.

    A source may call the supplier by a product/brand name while the catalogue
    already holds the legal operator.  Exact, unique product URLs are strong
    enough to reuse that operator; non-unique vendor homepages deliberately do
    not match.
    """
    if not website:
        return None
    rows = connection.execute(
        "SELECT DISTINCT company_id FROM products WHERE website = ?", (website,)
    ).fetchall()
    return int(rows[0][0]) if len(rows) == 1 else None


def product_from_unique_website(connection: sqlite3.Connection, website: str | None) -> int | None:
    """Return a product only when an exact URL identifies one product."""
    if not website:
        return None
    rows = connection.execute("SELECT id FROM products WHERE website = ?", (website,)).fetchall()
    return int(rows[0][0]) if len(rows) == 1 else None


def import_bundle(connection: sqlite3.Connection, bundle: dict[str, Any], source_path: Path) -> bool:
    record_id = bundle["record_id"]
    content_hash = bundle_hash(bundle)
    existing = connection.execute("SELECT content_hash FROM imports WHERE record_id = ?", (record_id,)).fetchone()
    if existing:
        if existing[0] != content_hash:
            raise BundleError(f"{source_path}: record_id '{record_id}' esiste ma il contenuto è differente")
        return False

    now = bundle["created_at"]
    created_by = bundle["created_by"]["agent_id"]
    entity_map: dict[str, tuple[str, int]] = {}
    source_map: dict[str, int] = {}

    with connection:
        for entity in bundle["entities"]:
            entity_type = entity["entity_type"]
            name = entity["name"].strip()
            metadata = json_value(entity.get("metadata"))
            if entity_type == "group":
                existing_id = find_row_id(connection, "company_groups", "name = ? COLLATE NOCASE", (name,))
                if existing_id is None:
                    cursor = connection.execute(
                        """INSERT INTO company_groups(name, legal_name, website, headquarters_country, metadata_json, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (name, entity.get("legal_name"), entity.get("website"), entity.get("headquarters_country"), metadata, now, now),
                    )
                    existing_id = int(cursor.lastrowid)
                entity_map[entity["local_id"]] = ("group", existing_id)
            elif entity_type == "company":
                vat_id = entity.get("identifiers", {}).get("vat_id")
                existing_id = None
                if vat_id:
                    existing_id = find_row_id(connection, "companies", "vat_id = ?", (vat_id,))
                if existing_id is None:
                    existing_id = find_row_id(connection, "companies", "name = ? COLLATE NOCASE", (name,))
                if existing_id is None:
                    existing_id = company_from_unique_product_website(connection, entity.get("website"))
                if existing_id is None:
                    cursor = connection.execute(
                        """INSERT INTO companies(
                            name, legal_name, vat_id, website, headquarters_city, headquarters_region,
                            headquarters_country, founded_year, employee_band, metadata_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            name, entity.get("legal_name"), vat_id, entity.get("website"),
                            entity.get("headquarters_city"), entity.get("headquarters_region"),
                            entity.get("headquarters_country", "IT"), entity.get("founded_year"),
                            entity.get("employee_band"), metadata, now, now,
                        ),
                    )
                    existing_id = int(cursor.lastrowid)
                entity_map[entity["local_id"]] = ("company", existing_id)
            else:  # product
                company_id = entity_map[entity["company_ref"]][1]
                slug = entity.get("slug") or slugify(name)
                existing_id = find_row_id(connection, "products", "company_id = ? AND slug = ?", (company_id, slug))
                if existing_id is None:
                    existing_id = product_from_unique_website(connection, entity.get("website"))
                if existing_id is None:
                    cursor = connection.execute(
                        """INSERT INTO products(
                            company_id, name, slug, website, status, deployment, description, metadata_json, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            company_id, name, slug, entity.get("website"), entity.get("status", "active"),
                            json_value(entity.get("deployment")), entity.get("description"), metadata, now, now,
                        ),
                    )
                    existing_id = int(cursor.lastrowid)
                entity_map[entity["local_id"]] = ("product", existing_id)

        for entity in bundle["entities"]:
            if entity["entity_type"] == "company" and entity.get("group_ref"):
                company_id = entity_map[entity["local_id"]][1]
                group_id = entity_map[entity["group_ref"]][1]
                connection.execute(
                    """INSERT OR IGNORE INTO company_group_memberships(company_id, group_id, relationship_type, evidence_excerpt)
                       VALUES (?, ?, ?, ?)""",
                    (company_id, group_id, entity.get("group_relationship", "member"), entity.get("group_evidence_excerpt")),
                )

        for source in bundle["sources"]:
            source_id = find_row_id(connection, "sources", "canonical_url = ?", (source["url"],))
            if source_id is None:
                cursor = connection.execute(
                    """INSERT INTO sources(
                        canonical_url, source_type, publisher, title, published_at, accessed_at, language, content_hash, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        source["url"], source["source_type"], source.get("publisher"), source.get("title"),
                        source.get("published_at"), source["accessed_at"], source.get("language", "it"),
                        source.get("content_hash"), json_value(source.get("metadata")),
                    ),
                )
                source_id = int(cursor.lastrowid)
            source_map[source["local_id"]] = source_id

        for document in bundle.get("documents", []):
            source_id = source_map[document["source_ref"]]
            existing_id = find_row_id(connection, "documents", "source_id = ?", (source_id,))
            if existing_id is not None:
                continue
            cursor = connection.execute(
                """INSERT INTO documents(
                    source_id, document_type, title, extracted_text, extraction_method, storage_path, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source_id, document.get("document_type", "web_page"), document.get("title"), document["text"],
                    document.get("extraction_method"), document.get("storage_path"), json_value(document.get("metadata")), now,
                ),
            )
            document_id = int(cursor.lastrowid)
            for index, (char_start, char_end, part) in enumerate(chunk_text(document["text"])):
                connection.execute(
                    """INSERT INTO document_chunks(document_id, chunk_index, heading, text, char_start, char_end)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (document_id, index, document.get("title"), part, char_start, char_end),
                )

        for item in bundle.get("industry_classifications", []):
            company_id = entity_map[item["company_ref"]][1]
            system = item.get("classification_system", "ATECO")
            connection.execute(
                """INSERT INTO industry_codes(
                    classification_system, classification_version, code, label, parent_code, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(classification_system, classification_version, code) DO UPDATE SET
                    label=COALESCE(excluded.label, industry_codes.label),
                    parent_code=COALESCE(excluded.parent_code, industry_codes.parent_code)""",
                (system, item["classification_version"], item["code"], item.get("label"), item.get("parent_code"), json_value(item.get("metadata"))),
            )
            code_id = find_row_id(
                connection, "industry_codes", "classification_system = ? AND classification_version = ? AND code = ?",
                (system, item["classification_version"], item["code"]),
            )
            connection.execute(
                """INSERT INTO company_industry_codes(
                    company_id, industry_code_id, role, valid_from, valid_to, source_id, evidence_excerpt
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(company_id, industry_code_id) DO UPDATE SET
                    role=excluded.role, valid_from=excluded.valid_from, valid_to=excluded.valid_to,
                    source_id=excluded.source_id, evidence_excerpt=excluded.evidence_excerpt""",
                (
                    company_id, code_id, item["role"], item.get("valid_from"), item.get("valid_to"),
                    source_map[item["source_ref"]], item.get("evidence_excerpt"),
                ),
            )

        for item in bundle.get("classifications", []):
            product_id = entity_map[item["subject_ref"]][1]
            parent_id = None
            if item.get("parent_slug"):
                parent_id = find_row_id(connection, "taxonomy_terms", "kind = ? AND slug = ?", (item["kind"], item["parent_slug"]))
            connection.execute(
                """INSERT INTO taxonomy_terms(kind, name, slug, parent_id, description, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(kind, slug) DO UPDATE SET name=excluded.name""",
                (item["kind"], item["term_name"], item["term_slug"], parent_id, item.get("description"), json_value(item.get("metadata"))),
            )
            term_id = find_row_id(connection, "taxonomy_terms", "kind = ? AND slug = ?", (item["kind"], item["term_slug"]))
            connection.execute(
                """INSERT INTO product_terms(product_id, term_id, relevance, confidence, source_id, evidence_excerpt)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(product_id, term_id) DO UPDATE SET
                    relevance=excluded.relevance, confidence=excluded.confidence, source_id=excluded.source_id,
                    evidence_excerpt=excluded.evidence_excerpt""",
                (product_id, term_id, item.get("relevance", 1.0), item["confidence"], source_map[item["source_ref"]], item.get("evidence_excerpt")),
            )

        for item in bundle.get("features", []):
            product_id = entity_map[item["subject_ref"]][1]
            connection.execute(
                """INSERT INTO features(name, slug, feature_group, description, metadata_json)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(slug) DO UPDATE SET name=excluded.name""",
                (item["feature_name"], item["feature_slug"], item.get("feature_group"), item.get("description"), json_value(item.get("metadata"))),
            )
            feature_id = find_row_id(connection, "features", "slug = ?", (item["feature_slug"],))
            connection.execute(
                """INSERT INTO product_features(product_id, feature_id, support_level, confidence, source_id, evidence_excerpt)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(product_id, feature_id) DO UPDATE SET
                    support_level=excluded.support_level, confidence=excluded.confidence, source_id=excluded.source_id,
                    evidence_excerpt=excluded.evidence_excerpt""",
                (product_id, feature_id, item["support_level"], item["confidence"], source_map[item["source_ref"]], item.get("evidence_excerpt")),
            )

        for item in bundle.get("technical_characteristics", []):
            product_id = entity_map[item["subject_ref"]][1]
            connection.execute(
                """INSERT INTO technical_terms(kind, name, slug, description, metadata_json)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(kind, slug) DO UPDATE SET name=excluded.name""",
                (item["kind"], item["term_name"], item["term_slug"], item.get("description"), json_value(item.get("metadata"))),
            )
            term_id = find_row_id(connection, "technical_terms", "kind = ? AND slug = ?", (item["kind"], item["term_slug"]))
            connection.execute(
                """INSERT INTO product_technical_terms(
                    product_id, technical_term_id, relationship_type, confidence, source_id, evidence_excerpt
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(product_id, technical_term_id) DO UPDATE SET
                    relationship_type=excluded.relationship_type, confidence=excluded.confidence,
                    source_id=excluded.source_id, evidence_excerpt=excluded.evidence_excerpt""",
                (product_id, term_id, item["relationship_type"], item["confidence"], source_map[item["source_ref"]], item.get("evidence_excerpt")),
            )

        for item in bundle.get("financial_metrics", []):
            subject_type, subject_id = entity_map[item["subject_ref"]]
            value = item["value"]
            connection.execute(
                """INSERT INTO financial_metrics(
                    subject_type, subject_id, metric, period_year, value_exact, value_min, value_max, currency,
                    value_kind, methodology, confidence, source_id, evidence_excerpt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    subject_type, subject_id, item["metric"], item["period_year"], value.get("exact"), value.get("min"),
                    value.get("max"), item.get("currency"), item["value_kind"], item.get("methodology"), item["confidence"],
                    source_map[item["source_ref"]], item.get("evidence_excerpt"),
                ),
            )

        for item in bundle.get("facts", []):
            subject_type, subject_id = entity_map[item["subject_ref"]]
            value_text, value_number, value_boolean, value_json = scalar_value(item["value"])
            connection.execute(
                """INSERT INTO facts(
                    subject_type, subject_id, predicate, value_text, value_number, value_boolean, value_json, unit,
                    valid_from, valid_to, value_kind, methodology, confidence, source_id, evidence_excerpt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    subject_type, subject_id, item["predicate"], value_text, value_number, value_boolean, value_json,
                    item.get("unit"), item.get("valid_from"), item.get("valid_to"), item["value_kind"], item.get("methodology"),
                    item["confidence"], source_map[item["source_ref"]], item.get("evidence_excerpt"),
                ),
            )

        for item in bundle.get("claims", []):
            subject_type, subject_id = entity_map[item["subject_ref"]]
            connection.execute(
                """INSERT INTO claims(
                    subject_type, subject_id, claim_type, predicate, statement, assessment, methodology, confidence,
                    source_id, evidence_excerpt, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    subject_type, subject_id, item["claim_type"], item["predicate"], item["statement"], item.get("assessment"),
                    item.get("methodology"), item["confidence"], source_map[item["source_ref"]], item.get("evidence_excerpt"),
                    created_by, now,
                ),
            )

        for item in bundle.get("notes", []):
            subject_type, subject_id = entity_map[item["subject_ref"]]
            connection.execute(
                """INSERT INTO notes(subject_type, subject_id, note_type, text, confidence, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (subject_type, subject_id, item["note_type"], item["text"], item.get("confidence"), created_by, now),
            )

        connection.execute(
            """INSERT INTO imports(record_id, content_hash, source_path, imported_at, importer_version, supersedes_record_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (record_id, content_hash, str(source_path), datetime.now(timezone.utc).isoformat(), IMPORTER_VERSION, bundle.get("supersedes_record_id")),
        )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON bundle or directory to scan recursively")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "catalog.sqlite")
    parser.add_argument(
        "--skip-web-export", action="store_true",
        help="non rigenerare web/catalog-data.js dopo un import nel catalogo locale predefinito",
    )
    args = parser.parse_args()
    if not args.database.exists():
        print(f"ERRORE: database non trovato: {args.database}. Esegui scripts/init_db.py prima.")
        return 2
    try:
        paths = list(paths_from_input(args.input))
    except BundleError as exc:
        print(f"ERRORE: {exc}")
        return 2
    if not paths:
        print("Nessun bundle JSON trovato.")
        return 1

    connection = sqlite3.connect(args.database)
    connection.execute("PRAGMA foreign_keys = ON")
    imported = skipped = failed = 0
    try:
        for path in paths:
            try:
                bundle = load_bundle(path)
                errors = validate_bundle(bundle)
                if errors:
                    raise BundleError("; ".join(errors))
                if import_bundle(connection, bundle, path):
                    imported += 1
                    print(f"IMPORTATO  {path}")
                else:
                    skipped += 1
                    print(f"GIÀ IMPORTATO  {path}")
            except (BundleError, sqlite3.Error, KeyError, TypeError) as exc:
                failed += 1
                print(f"ERRORE     {path}: {exc}")
    finally:
        connection.close()
    print(f"Risultato: importati={imported}, già importati={skipped}, errori={failed}")
    if imported and not args.skip_web_export and args.database.resolve() == (ROOT / "data" / "catalog.sqlite").resolve():
        from export_web_data import export_catalogue

        count = export_catalogue(args.database, ROOT / "web" / "catalog-data.js")
        print(f"Mappa web aggiornata: {count} prodotti esportati in web/catalog-data.js")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
