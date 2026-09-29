from pathlib import Path
import hashlib
import json
import tempfile
import unittest

from personal_wiki.config import AppPaths, load_page_specs
from personal_wiki.ingest import IngestService
from personal_wiki.retrieval import PassageIndex
from personal_wiki.wiki_pages import validate_page_specs, validate_wiki

from tests.helpers import FakeClient, write_json


ROOT = Path(__file__).resolve().parents[1]


class WikiTests(unittest.TestCase):
    def test_configured_titles_are_short_and_links_resolve(self):
        specs = load_page_specs(AppPaths(ROOT))
        self.assertEqual([], validate_page_specs(specs))
        self.assertEqual(5, len(specs))

    def test_reingestion_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "vault" / "raw"
            raw.mkdir(parents=True)
            source_path = raw / "Source Note.txt"
            source_path.write_text(
                "Payment determines access. Reimbursement can influence provider behavior and value.",
                encoding="utf-8",
            )
            digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            write_json(
                root / "data" / "source_catalog.json",
                {
                    "sources": [
                        {
                            "source_id": "source-note",
                            "title": "Source Note",
                            "path": "vault/raw/Source Note.txt",
                            "sha256": digest,
                            "source_type": "txt",
                            "author": "Tester",
                            "date": "2026-01-01",
                            "provenance": "Test",
                            "permission": "Test",
                        }
                    ]
                },
            )
            write_json(
                root / "config" / "wiki_pages.json",
                {
                    "pages": [
                        {
                            "page_id": "payment-access",
                            "title": "Payment and Access",
                            "folder": "Concepts",
                            "focus_query": "payment reimbursement access provider value",
                            "source_ids": ["source-note"],
                            "related": [],
                        }
                    ]
                },
            )
            write_json(root / "config" / "retrieval.json", {"synonyms": {}})
            (root / "prompts").mkdir()
            (root / "prompts" / "ingest.md").write_text("Use only evidence.", encoding="utf-8")
            write_json(root / "data" / "generation_state.json", {"version": 1, "pages": {}})
            client = FakeClient(
                [
                    {
                        "summary": "Payment design affects access and behavior.",
                        "details": [
                            {"heading": "Access", "paragraph": "Reimbursement can affect access."},
                            {"heading": "Behavior", "paragraph": "Payment can influence providers."},
                        ],
                        "limitations": "The note is brief.",
                    }
                ]
            )
            paths = AppPaths(root)
            index = PassageIndex(paths.database)
            service = IngestService(paths, index, client)
            first = service.run(raw)
            second = service.run(raw)
            self.assertEqual(["Payment and Access"], first["wiki_pages"]["generated"])
            self.assertEqual(["Payment and Access"], second["wiki_pages"]["skipped"])
            self.assertEqual(1, len(client.calls))
            pages = list((root / "vault" / "wiki").rglob("*.md"))
            self.assertEqual(1, len(pages))
            self.assertEqual("Payment and Access", pages[0].stem)

    def test_heading_and_internal_link_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "config" / "wiki_pages.json",
                {
                    "pages": [
                        {
                            "page_id": "one",
                            "title": "Readable Note",
                            "folder": "Concepts",
                            "focus_query": "topic",
                            "source_ids": [],
                            "related": [],
                        }
                    ]
                },
            )
            page = root / "vault" / "wiki" / "Concepts" / "Readable Note.md"
            page.parent.mkdir(parents=True)
            page.write_text("# Wrong Heading\n\n[[Missing Note]]\n", encoding="utf-8")
            errors = validate_wiki(AppPaths(root))
            self.assertTrue(any("mismatch" in error for error in errors))
            self.assertTrue(any("Broken internal link" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
