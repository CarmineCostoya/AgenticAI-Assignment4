from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from personal_wiki.models import ModelResponse, ModelRunMetrics


class FakeClient:
    def __init__(self, responses: List[Any], model: str = "gemma3:1b-it-q4_K_M"):
        self.responses = list(responses)
        self.model = model
        self.calls: List[Dict[str, Any]] = []

    def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        if not self.responses:
            raise AssertionError("Unexpected model call")
        value = self.responses.pop(0)
        content = value if isinstance(value, str) else json.dumps(value)
        return ModelResponse(
            content=content,
            model=self.model,
            raw={"model": self.model},
            metrics=ModelRunMetrics(wall_seconds=0.01, prompt_tokens=10, generated_tokens=5),
        )

    def list_models(self):
        return [self.model]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
