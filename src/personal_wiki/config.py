from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from .models import SourceRecord, WikiPageSpec


DEFAULT_MODEL = "gemma3:1b-it-q4_K_M"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        override = os.environ.get("WIKI_PROJECT_ROOT")
        if override:
            return cls(Path(override).expanduser().resolve())
        return cls(Path(__file__).resolve().parents[2])

    @property
    def config_dir(self) -> Path:
        return self.root / "config"

    @property
    def prompts_dir(self) -> Path:
        return self.root / "prompts"

    @property
    def vault(self) -> Path:
        return self.root / "vault"

    @property
    def data(self) -> Path:
        return self.root / "data"

    @property
    def evidence(self) -> Path:
        return self.root / "evidence"

    @property
    def database(self) -> Path:
        return self.data / "index.sqlite3"

    @property
    def source_catalog(self) -> Path:
        return self.data / "source_catalog.json"

    @property
    def generation_state(self) -> Path:
        return self.data / "generation_state.json"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_sources(paths: AppPaths) -> List[SourceRecord]:
    payload = _load_json(paths.source_catalog)
    return [SourceRecord(**item) for item in payload["sources"]]


def load_page_specs(paths: AppPaths) -> List[WikiPageSpec]:
    payload = _load_json(paths.config_dir / "wiki_pages.json")
    return [WikiPageSpec(**item) for item in payload["pages"]]


def load_synonyms(paths: AppPaths) -> Dict[str, List[str]]:
    return _load_json(paths.config_dir / "retrieval.json")["synonyms"]


def read_prompt(paths: AppPaths, name: str) -> str:
    return (paths.prompts_dir / name).read_text(encoding="utf-8").strip()


def model_name() -> str:
    return os.environ.get("WIKI_MODEL", DEFAULT_MODEL)


def ollama_url() -> str:
    return os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL).rstrip("/")
