from pathlib import Path
import tempfile
import unittest

from personal_wiki.models import Passage
from personal_wiki.retrieval import PassageIndex


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.index = PassageIndex(
            Path(self.tempdir.name) / "index.sqlite3",
            {
                "payment": ["reimbursement"],
                "access": ["reach", "coverage"],
                "approval": ["approved", "regulatory"],
            },
        )
        self.index.rebuild(
            [
                Passage("one", "a", "raw/a.pdf", "slide 6", "Regulatory approval does not guarantee reimbursement, coverage, or true access."),
                Passage("two", "b", "raw/b.pdf", "slide 10", "Payment models range from fee for service to two-sided risk."),
            ]
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_synonyms_find_paraphrased_passage_without_model(self):
        hits = self.index.search("Why can an approved product fail to reach someone?", limit=2)
        self.assertEqual("one", hits[0].chunk_id)
        self.assertGreaterEqual(hits[0].query_coverage, 2)

    def test_search_returns_original_text_and_location(self):
        hits = self.index.search("fee service risk")
        self.assertEqual("slide 10", hits[0].locator)
        self.assertIn("two-sided risk", hits[0].text)

    def test_source_filter_is_applied(self):
        hits = self.index.search("payment", source_ids=["a"])
        self.assertEqual(["a"], [hit.source_id for hit in hits])


if __name__ == "__main__":
    unittest.main()
