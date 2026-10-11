#!/usr/bin/env python3
"""Merge explicitly reviewed duplicate products and companies in one transaction.

This is deliberately not a fuzzy deduplicator. Every source and destination id is
passed on the command line after human/agent review. `--apply` is required for a
write; otherwise the script prints the reviewed merge plan.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_pair(value: str) -> tuple[int, int]:
    try:
        duplicate, canonical = (int(part) for part in value.split(":", 1))
    except ValueError as error:
        raise argparse.ArgumentTypeError("use DUPLICATE_ID:CANONICAL_ID") from error
    if duplicate == canonical:
        raise argparse.ArgumentTypeError("duplicate and canonical ids must differ")
    return duplicate, canonical


def one(connection: sqlite3.Connection, query: str, entity_id: int) -> tuple[int, str]:
    row = connection.execute(query, (entity_id,)).fetchone()
    if row is None:
        raise ValueError(f"missing entity id {entity_id}")
    return row


def move_product(connection: sqlite3.Connection, duplicate: int, canonical: int) -> None:
    duplicate_row = one(connection, "SELECT id, name FROM products WHERE id = ?", duplicate)
    canonical_row = one(connection, "SELECT id, name FROM products WHERE id = ?", canonical)
    print(f"product {duplicate_row[0]} ({duplicate_row[1]}) -> {canonical_row[0]} ({canonical_row[1]})")
    for table, column in (
        ("product_terms", "term_id"),
        ("product_features", "feature_id"),
        ("product_technical_terms", "technical_term_id"),
    ):
        connection.execute(
            f"INSERT OR IGNORE INTO {table} SELECT ?, {column}, "
            + ("relevance, confidence, source_id, evidence_excerpt" if table == "product_terms" else "support_level, confidence, source_id, evidence_excerpt" if table == "product_features" else "relationship_type, confidence, source_id, evidence_excerpt")
            + f" FROM {table} WHERE product_id = ?",
            (canonical, duplicate),
        )
        connection.execute(f"DELETE FROM {table} WHERE product_id = ?", (duplicate,))
    for table in ("facts", "claims", "notes", "financial_metrics"):
        connection.execute(
            f"UPDATE {table} SET subject_id = ? WHERE subject_type = 'product' AND subject_id = ?",
            (canonical, duplicate),
        )
    connection.execute("DELETE FROM products WHERE id = ?", (duplicate,))


def move_company(connection: sqlite3.Connection, duplicate: int, canonical: int) -> None:
    duplicate_row = one(connection, "SELECT id, name FROM companies WHERE id = ?", duplicate)
    canonical_row = one(connection, "SELECT id, name FROM companies WHERE id = ?", canonical)
    print(f"company {duplicate_row[0]} ({duplicate_row[1]}) -> {canonical_row[0]} ({canonical_row[1]})")
    connection.execute(
        "INSERT OR IGNORE INTO company_group_memberships "
        "SELECT ?, group_id, relationship_type, source_id, evidence_excerpt FROM company_group_memberships WHERE company_id = ?",
        (canonical, duplicate),
    )
    connection.execute("DELETE FROM company_group_memberships WHERE company_id = ?", (duplicate,))
    connection.execute(
        "INSERT OR IGNORE INTO company_industry_codes "
        "SELECT ?, industry_code_id, role, valid_from, valid_to, source_id, evidence_excerpt FROM company_industry_codes WHERE company_id = ?",
        (canonical, duplicate),
    )
    connection.execute("DELETE FROM company_industry_codes WHERE company_id = ?", (duplicate,))
    connection.execute("UPDATE products SET company_id = ? WHERE company_id = ?", (canonical, duplicate))
    for table in ("facts", "claims", "notes", "financial_metrics"):
        connection.execute(
            f"UPDATE {table} SET subject_id = ? WHERE subject_type = 'company' AND subject_id = ?",
            (canonical, duplicate),
        )
    connection.execute("DELETE FROM companies WHERE id = ?", (duplicate,))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "catalog.sqlite")
    parser.add_argument("--product", type=parse_pair, action="append", default=[], metavar="DUP:CANON")
    parser.add_argument("--company", type=parse_pair, action="append", default=[], metavar="DUP:CANON")
    parser.add_argument("--apply", action="store_true", help="perform the reviewed merge")
    args = parser.parse_args()
    if not args.product and not args.company:
        parser.error("provide at least one --product or --company mapping")

    connection = sqlite3.connect(args.database)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        if not args.apply:
            for duplicate, canonical in args.product:
                move_product_preview = one(connection, "SELECT id, name FROM products WHERE id = ?", duplicate)
                canonical_preview = one(connection, "SELECT id, name FROM products WHERE id = ?", canonical)
                print(f"WOULD MERGE product {move_product_preview} -> {canonical_preview}")
            for duplicate, canonical in args.company:
                duplicate_preview = one(connection, "SELECT id, name FROM companies WHERE id = ?", duplicate)
                canonical_preview = one(connection, "SELECT id, name FROM companies WHERE id = ?", canonical)
                print(f"WOULD MERGE company {duplicate_preview} -> {canonical_preview}")
            return 0
        with connection:
            for duplicate, canonical in args.product:
                move_product(connection, duplicate, canonical)
            for duplicate, canonical in args.company:
                move_company(connection, duplicate, canonical)
        print("Merge completed.")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
