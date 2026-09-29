from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    title: str
    path: str
    sha256: str
    source_type: str
    author: str
    date: str
    provenance: str
    permission: str


@dataclass(frozen=True)
class Passage:
    chunk_id: str
    source_id: str
    source_path: str
    locator: str
    text: str


@dataclass(frozen=True)
class SearchHit:
    chunk_id: str
    source_id: str
    source_path: str
    locator: str
    text: str
    score: float
    query_coverage: int = 0
    evidence_id: str = ""


@dataclass(frozen=True)
class WikiPageSpec:
    page_id: str
    title: str
    folder: str
    focus_query: str
    source_ids: List[str]
    related: List[Dict[str, str]]

    @property
    def relative_path(self) -> Path:
        return Path("wiki") / self.folder / f"{self.title}.md"


@dataclass(frozen=True)
class ChatRoute:
    retrieve: bool
    query: str
    reason: str


@dataclass(frozen=True)
class SupportedClaim:
    text: str
    evidence_ids: List[str]


@dataclass
class ModelRunMetrics:
    wall_seconds: float = 0.0
    total_duration_seconds: Optional[float] = None
    load_duration_seconds: Optional[float] = None
    prompt_tokens: Optional[int] = None
    generated_tokens: Optional[int] = None
    ollama_rss_mb: Optional[float] = None
    model_size_mb: Optional[float] = None
    model_vram_mb: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelResponse:
    content: str
    model: str
    raw: Dict[str, Any]
    metrics: ModelRunMetrics


@dataclass
class AskResult:
    question: str
    supported: bool
    rendered_answer: str
    raw_model_output: str
    hits: List[SearchHit] = field(default_factory=list)
    claims: List[SupportedClaim] = field(default_factory=list)
    reason: str = ""
    metrics: Optional[ModelRunMetrics] = None


@dataclass
class ChatResult:
    text: str
    route: ChatRoute
    raw_model_output: str
    hits: List[SearchHit] = field(default_factory=list)
    metrics: Optional[ModelRunMetrics] = None
