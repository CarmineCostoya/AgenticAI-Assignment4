from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from .models import Passage, SourceRecord


class ExtractionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk_words(text: str, target_words: int = 350, overlap_words: int = 60) -> List[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= target_words:
        return [" ".join(words)]
    chunks: List[str] = []
    start = 0
    step = max(1, target_words - overlap_words)
    while start < len(words):
        end = min(len(words), start + target_words)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks


def extract_pdf(path: Path, source: SourceRecord) -> List[Passage]:
    try:
        import pdfplumber
    except ImportError as exc:
        raise ExtractionError("pdfplumber is required for PDF ingestion") from exc

    passages: List[Passage] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = normalize_text(page.extract_text() or "")
                if not text:
                    continue
                passages.append(
                    Passage(
                        chunk_id=f"{source.source_id}:slide-{page_number}",
                        source_id=source.source_id,
                        source_path=source.path,
                        locator=f"slide {page_number}",
                        text=text,
                    )
                )
    except Exception as exc:
        raise ExtractionError(f"Could not extract {path}: {exc}") from exc
    return passages


def _docx_sections(path: Path) -> List[Tuple[str, str]]:
    try:
        from docx import Document
    except ImportError as exc:
        raise ExtractionError("python-docx is required for DOCX ingestion") from exc

    document = Document(str(path))
    sections: List[Tuple[str, List[str]]] = []
    current_title = "Opening"
    current_paragraphs: List[str] = []

    def flush() -> None:
        nonlocal current_paragraphs
        if current_paragraphs:
            sections.append((current_title, current_paragraphs))
            current_paragraphs = []

    for paragraph in document.paragraphs:
        text = normalize_text(paragraph.text)
        if not text:
            continue
        style_name = getattr(paragraph.style, "name", "") or ""
        if style_name.lower().startswith(("heading", "title")):
            flush()
            current_title = text
        else:
            current_paragraphs.append(text)
    flush()
    return [(title, "\n\n".join(paragraphs)) for title, paragraphs in sections]


def extract_docx(path: Path, source: SourceRecord) -> List[Passage]:
    passages: List[Passage] = []
    try:
        sections = _docx_sections(path)
    except Exception as exc:
        if isinstance(exc, ExtractionError):
            raise
        raise ExtractionError(f"Could not extract {path}: {exc}") from exc

    for section_index, (heading, text) in enumerate(sections, start=1):
        chunks = _chunk_words(text)
        for part_index, chunk in enumerate(chunks, start=1):
            suffix = f", part {part_index}" if len(chunks) > 1 else ""
            passages.append(
                Passage(
                    chunk_id=f"{source.source_id}:section-{section_index}:part-{part_index}",
                    source_id=source.source_id,
                    source_path=source.path,
                    locator=f'section "{heading}"{suffix}',
                    text=chunk,
                )
            )
    return passages


def extract_source(root: Path, source: SourceRecord) -> List[Passage]:
    path = root / source.path
    if not path.exists():
        raise ExtractionError(f"Missing source: {source.path}")
    actual_hash = sha256_file(path)
    if actual_hash != source.sha256:
        raise ExtractionError(
            f"Source hash mismatch for {source.path}: expected {source.sha256}, got {actual_hash}"
        )
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path, source)
    if suffix == ".docx":
        return extract_docx(path, source)
    if suffix in {".md", ".txt"}:
        text = normalize_text(path.read_text(encoding="utf-8"))
        return [
            Passage(
                chunk_id=f"{source.source_id}:part-{index}",
                source_id=source.source_id,
                source_path=source.path,
                locator=f"part {index}",
                text=chunk,
            )
            for index, chunk in enumerate(_chunk_words(text), start=1)
        ]
    raise ExtractionError(f"Unsupported source type: {path.suffix}")
