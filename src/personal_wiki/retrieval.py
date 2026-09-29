from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .models import Passage, SearchHit


STOPWORDS = {
    "about", "according", "after", "again", "against", "also", "and", "are",
    "because", "been", "before", "being", "between", "can", "course", "did",
    "does", "doing", "each", "fail", "for", "from", "have", "healthcare",
    "into", "materials", "more", "most", "other", "our", "patient", "patients",
    "reach", "should", "source", "sources", "still", "than", "that", "the",
    "their", "these", "they", "this", "through", "toward", "under", "use",
    "used", "what", "when", "where", "which", "while", "why", "with", "would",
}


def tokenize(text: str) -> List[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9]+", text) if len(token) > 1]


class PassageIndex:
    def __init__(self, path: Path, synonyms: Optional[Dict[str, List[str]]] = None):
        self.path = path
        self.synonyms = synonyms or {}

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.path))
        connection.row_factory = sqlite3.Row
        return connection

    def rebuild(self, passages: Iterable[Passage]) -> int:
        with self.connect() as connection:
            connection.execute("DROP TABLE IF EXISTS passages")
            connection.execute(
                """
                CREATE VIRTUAL TABLE passages USING fts5(
                    chunk_id UNINDEXED,
                    source_id UNINDEXED,
                    source_path UNINDEXED,
                    locator UNINDEXED,
                    text,
                    tokenize='porter unicode61'
                )
                """
            )
            rows = [
                (p.chunk_id, p.source_id, p.source_path, p.locator, p.text)
                for p in passages
            ]
            connection.executemany(
                "INSERT INTO passages(chunk_id, source_id, source_path, locator, text) VALUES (?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    def count(self) -> int:
        if not self.path.exists():
            return 0
        with self.connect() as connection:
            try:
                return int(connection.execute("SELECT count(*) FROM passages").fetchone()[0])
            except sqlite3.OperationalError:
                return 0

    def _concepts(self, query: str) -> List[Set[str]]:
        concepts: List[Set[str]] = []
        seen: Set[str] = set()
        reverse: Dict[str, str] = {}
        for canonical, variants in self.synonyms.items():
            for variant in [canonical] + variants:
                reverse[variant.lower()] = canonical.lower()

        for token in tokenize(query):
            canonical = reverse.get(token, token)
            if canonical in STOPWORDS or canonical in seen:
                continue
            seen.add(canonical)
            group = {canonical}
            group.update(item.lower() for item in self.synonyms.get(canonical, []))
            concepts.append(group)
        return concepts

    def _match_expression(self, query: str) -> str:
        terms: Set[str] = set()
        for concept in self._concepts(query):
            for term in concept:
                terms.update(tokenize(term))
        return " OR ".join(f'"{term}"' for term in sorted(terms))

    def concept_count(self, query: str) -> int:
        return len(self._concepts(query))

    def coverage(self, query: str, text: str) -> int:
        lowered = text.lower()
        return sum(1 for concept in self._concepts(query) if any(term in lowered for term in concept))

    def search(
        self,
        query: str,
        limit: int = 5,
        source_ids: Optional[Sequence[str]] = None,
    ) -> List[SearchHit]:
        if not self.path.exists():
            raise FileNotFoundError("Retrieval index is missing; run `wiki ingest` first")
        expression = self._match_expression(query)
        if not expression:
            return []
        sql = (
            "SELECT chunk_id, source_id, source_path, locator, text, bm25(passages) AS rank "
            "FROM passages WHERE passages MATCH ?"
        )
        params: List[object] = [expression]
        if source_ids:
            placeholders = ",".join("?" for _ in source_ids)
            sql += f" AND source_id IN ({placeholders})"
            params.extend(source_ids)
        sql += " ORDER BY rank ASC LIMIT ?"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [
            SearchHit(
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                source_path=row["source_path"],
                locator=row["locator"],
                text=row["text"],
                score=float(-row["rank"]),
                query_coverage=self.coverage(query, row["text"]),
                evidence_id=f"S{index}",
            )
            for index, row in enumerate(rows, start=1)
        ]
