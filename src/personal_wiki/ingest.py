from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from .config import AppPaths, load_sources
from .extractors import extract_source
from .ollama import OllamaClient
from .retrieval import PassageIndex
from .wiki_pages import WikiPageService


class IngestService:
    def __init__(self, paths: AppPaths, index: PassageIndex, client: OllamaClient):
        self.paths = paths
        self.index = index
        self.client = client

    def run(self, source_root: Path) -> Dict[str, Any]:
        expected_root = (self.paths.vault / "raw").resolve()
        if source_root.resolve() != expected_root:
            raise ValueError(f"This project ingests its curated raw directory: {expected_root}")
        started = time.perf_counter()
        sources = load_sources(self.paths)
        passages = []
        source_counts: Dict[str, int] = {}
        for source in sources:
            extracted = extract_source(self.paths.root, source)
            passages.extend(extracted)
            source_counts[source.source_id] = len(extracted)
        passage_count = self.index.rebuild(passages)
        page_results = WikiPageService(self.paths, self.index, self.client).generate_all()
        result: Dict[str, Any] = {
            "mode": "ingest",
            "execution": "local",
            "model": self.client.model,
            "source_count": len(sources),
            "passage_count": passage_count,
            "source_passages": source_counts,
            "wiki_pages": page_results,
            "wall_seconds": round(time.perf_counter() - started, 3),
        }
        runtime_path = self.paths.data / "runtime" / "last_ingest.json"
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
