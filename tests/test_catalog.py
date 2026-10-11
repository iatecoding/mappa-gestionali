#!/usr/bin/env python3
"""End-to-end smoke test using only the Python standard library."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class CatalogueWorkflowTest(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, *args], cwd=ROOT, check=False, text=True, capture_output=True
        )

    def test_demo_bundle_validates_imports_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "catalog.sqlite"
            init = self.run_script("scripts/init_db.py", "--database", str(database))
            self.assertEqual(init.returncode, 0, init.stderr + init.stdout)
            validate = self.run_script("scripts/validate_inbox.py", "examples/vendor-example.json")
            self.assertEqual(validate.returncode, 0, validate.stderr + validate.stdout)
            first_import = self.run_script("scripts/import_inbox.py", "examples/vendor-example.json", "--database", str(database))
            self.assertEqual(first_import.returncode, 0, first_import.stderr + first_import.stdout)
            self.assertIn("importati=1", first_import.stdout)
            overview = self.run_script("scripts/query_examples.py", "--database", str(database))
            self.assertEqual(overview.returncode, 0, overview.stderr + overview.stdout)
            self.assertIn("ATECO", overview.stdout)
            second_import = self.run_script("scripts/import_inbox.py", "examples/vendor-example.json", "--database", str(database))
            self.assertEqual(second_import.returncode, 0, second_import.stderr + second_import.stdout)
            self.assertIn("già importati=1", second_import.stdout)
            search = self.run_script("scripts/query_examples.py", "--database", str(database), "--search", "magazzino")
            self.assertEqual(search.returncode, 0, search.stderr + search.stdout)
            self.assertIn("magazzino", search.stdout.lower())

    def test_registry_deduplicates_candidates_and_urls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "research-state.sqlite"
            first = self.run_script(
                "scripts/research_registry.py", "--database", str(registry), "candidate-add",
                "--name", "Demo ERP", "--company", "Demo S.r.l.", "--vat-id", "12345678901",
                "--website", "https://example.com", "--method", "test",
            )
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            second = self.run_script(
                "scripts/research_registry.py", "--database", str(registry), "candidate-add",
                "--name", "Altro nome", "--company", "Demo S.r.l.", "--vat-id", "12345678901",
                "--website", "https://example.com", "--method", "test",
            )
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            self.assertIn('"result": "existing"', second.stdout)
            lease = self.run_script(
                "scripts/research_registry.py", "--database", str(registry), "reserve",
                "--url", "https://example.com/a?utm_source=test", "--agent", "agent-a", "--purpose", "test",
            )
            self.assertEqual(lease.returncode, 0, lease.stderr + lease.stdout)
            busy = self.run_script(
                "scripts/research_registry.py", "--database", str(registry), "reserve",
                "--url", "https://example.com/a", "--agent", "agent-b", "--purpose", "test",
            )
            self.assertEqual(busy.returncode, 3, busy.stderr + busy.stdout)


if __name__ == "__main__":
    unittest.main()
