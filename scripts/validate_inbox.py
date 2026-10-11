#!/usr/bin/env python3
"""Validate research bundles before they reach SQLite."""

from __future__ import annotations

import argparse
from pathlib import Path

from catalog_lib import BundleError, load_bundle, paths_from_input, validate_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON bundle or directory to scan recursively")
    args = parser.parse_args()
    try:
        paths = list(paths_from_input(args.input))
    except BundleError as exc:
        print(f"ERRORE: {exc}")
        return 2
    if not paths:
        print("Nessun bundle JSON trovato.")
        return 1

    failed = 0
    for path in paths:
        try:
            errors = validate_bundle(load_bundle(path))
        except BundleError as exc:
            errors = [str(exc)]
        if errors:
            failed += 1
            print(f"NON VALIDO  {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"VALIDO      {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
