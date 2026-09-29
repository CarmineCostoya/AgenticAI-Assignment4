from pathlib import Path
import unittest

from personal_wiki.config import AppPaths, load_sources
from personal_wiki.extractors import _chunk_words, extract_source, sha256_file


ROOT = Path(__file__).resolve().parents[1]


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.paths = AppPaths(ROOT)
        self.sources = {item.source_id: item for item in load_sources(self.paths)}

    def test_committed_sources_match_catalog_hashes(self):
        for source in self.sources.values():
            self.assertEqual(source.sha256, sha256_file(ROOT / source.path))

    def test_pdf_passages_preserve_slide_locators(self):
        source = self.sources["structure-costs-2026-08-31"]
        passages = extract_source(ROOT, source)
        self.assertEqual(16, len(passages))
        self.assertEqual("slide 1", passages[0].locator)
        self.assertEqual("slide 16", passages[-1].locator)
        self.assertIn("Dimensions", passages[2].text)

    def test_docx_passages_preserve_section_locators(self):
        source = self.sources["study-guide-2026"]
        passages = extract_source(ROOT, source)
        self.assertGreater(len(passages), 5)
        self.assertTrue(all(item.locator.startswith("section") for item in passages))
        self.assertTrue(any("Healthcare has no single definition of value" in item.locator for item in passages))

    def test_long_chunks_overlap_by_sixty_words(self):
        words = [f"word{index}" for index in range(700)]
        chunks = _chunk_words(" ".join(words), target_words=350, overlap_words=60)
        self.assertEqual(words[290:350], chunks[1].split()[:60])
        self.assertLessEqual(max(len(chunk.split()) for chunk in chunks), 350)


if __name__ == "__main__":
    unittest.main()
