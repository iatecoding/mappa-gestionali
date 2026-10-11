#!/usr/bin/env python3
"""Report riproducibile della copertura del catalogo e delle priorità di ricerca.

Non considera l'assenza di un prezzo come un dato negativo: evidenzia soltanto i
prodotti per cui non è stata ancora registrata un'evidenza commerciale.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def scalar(connection: sqlite3.Connection, query: str) -> int:
    return int(connection.execute(query).fetchone()[0])



def names(connection: sqlite3.Connection, query: str, limit: int) -> list[str]:
    return [row[0] for row in connection.execute(query + " LIMIT ?", (limit,))]



def section(title: str, count: int, total: int, missing: list[str]) -> None:
    percentage = 0 if total == 0 else round(count * 100 / total, 1)
    print(f"{title}: {count}/{total} ({percentage}%)")
    if missing:
        print("  Priorità: " + ", ".join(missing))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "catalog.sqlite")
    parser.add_argument("--limit", type=int, default=15, help="massimo di prodotti mostrati per lacuna")
    args = parser.parse_args()

    connection = sqlite3.connect(args.database)
    try:
        total_products = scalar(connection, "SELECT count(*) FROM products")
        total_companies = scalar(connection, "SELECT count(*) FROM companies")
        product_companies = scalar(connection, "SELECT count(DISTINCT company_id) FROM products")
        print("COPERTURA CATALOGO")
        print(f"Prodotti: {total_products}; aziende: {total_companies}; fonti: {scalar(connection, 'SELECT count(*) FROM sources')}")

        section(
            "Feature business (almeno 3)",
            scalar(connection, "SELECT count(*) FROM products p WHERE (SELECT count(*) FROM product_features pf WHERE pf.product_id = p.id) >= 3"),
            total_products,
            names(connection, "SELECT p.name FROM products p WHERE (SELECT count(*) FROM product_features pf WHERE pf.product_id = p.id) < 3 ORDER BY p.name", args.limit),
        )
        section(
            "Dettagli tecnici (almeno 2)",
            scalar(connection, "SELECT count(*) FROM products p WHERE (SELECT count(*) FROM product_technical_terms pt WHERE pt.product_id = p.id) >= 2"),
            total_products,
            names(connection, "SELECT p.name FROM products p WHERE (SELECT count(*) FROM product_technical_terms pt WHERE pt.product_id = p.id) < 2 ORDER BY p.name", args.limit),
        )
        section(
            "Evidenza commerciale (prezzo, prova, demo o preventivo)",
            scalar(connection, "SELECT count(*) FROM products p WHERE EXISTS (SELECT 1 FROM facts f WHERE f.subject_type = 'product' AND f.subject_id = p.id AND (f.predicate LIKE 'pricing.%' OR f.predicate LIKE 'trial.%'))"),
            total_products,
            names(connection, "SELECT p.name FROM products p WHERE NOT EXISTS (SELECT 1 FROM facts f WHERE f.subject_type = 'product' AND f.subject_id = p.id AND (f.predicate LIKE 'pricing.%' OR f.predicate LIKE 'trial.%')) ORDER BY p.name", args.limit),
        )
        section(
            "Produttori con metrica finanziaria",
            scalar(connection, "SELECT count(DISTINCT p.company_id) FROM products p WHERE EXISTS (SELECT 1 FROM financial_metrics fm WHERE fm.subject_type = 'company' AND fm.subject_id = p.company_id)"),
            product_companies,
            names(connection, "SELECT DISTINCT c.name FROM companies c JOIN products p ON p.company_id = c.id WHERE NOT EXISTS (SELECT 1 FROM financial_metrics fm WHERE fm.subject_type = 'company' AND fm.subject_id = c.id) ORDER BY c.name", args.limit),
        )
        section(
            "Produttori con P.IVA",
            scalar(connection, "SELECT count(DISTINCT p.company_id) FROM products p JOIN companies c ON c.id = p.company_id WHERE c.vat_id IS NOT NULL"),
            product_companies,
            names(connection, "SELECT DISTINCT c.name FROM companies c JOIN products p ON p.company_id = c.id WHERE c.vat_id IS NULL ORDER BY c.name", args.limit),
        )
        fk_errors = scalar(connection, "SELECT count(*) FROM pragma_foreign_key_check")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        print(f"Integrità SQLite: {integrity}; violazioni FK: {fk_errors}")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
