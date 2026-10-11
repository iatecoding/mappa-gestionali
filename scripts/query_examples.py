#!/usr/bin/env python3
"""Run a few inspection queries against the local catalogue."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

QUERIES = {
    "products": "SELECT product_name, company_name, status FROM v_product_overview ORDER BY company_name, product_name",
    "features": "SELECT product_name, feature_name, support_level, confidence FROM v_product_feature_matrix ORDER BY product_name, feature_name",
    "technical": "SELECT product_name, technical_kind, technical_name, relationship_type, confidence FROM v_product_technical_matrix ORDER BY product_name, technical_kind, technical_name",
    "ateco": "SELECT company_name, vat_id, classification_version, ateco_code, ateco_label FROM v_company_primary_ateco ORDER BY company_name",
    "revenue": "SELECT subject_id, period_year, value_exact, currency, value_kind, confidence FROM v_latest_company_revenue ORDER BY period_year DESC",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "catalog.sqlite")
    parser.add_argument("--search", help="query full text in document chunks")
    args = parser.parse_args()
    connection = sqlite3.connect(args.database)
    try:
        if args.search:
            rows = connection.execute(
                """SELECT s.canonical_url, snippet(document_chunks_fts, 1, '[', ']', '…', 12)
                   FROM document_chunks_fts
                   JOIN document_chunks dc ON dc.id = document_chunks_fts.rowid
                   JOIN documents d ON d.id = dc.document_id
                   JOIN sources s ON s.id = d.source_id
                   WHERE document_chunks_fts MATCH ?
                   ORDER BY rank""",
                (args.search,),
            ).fetchall()
            print("RICERCA TESTUALE")
            for url, excerpt in rows:
                print(f"- {excerpt}\n  {url}")
            return 0
        for label, query in QUERIES.items():
            print(f"\n{label.upper()}")
            for row in connection.execute(query):
                print(" | ".join("" if value is None else str(value) for value in row))
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
