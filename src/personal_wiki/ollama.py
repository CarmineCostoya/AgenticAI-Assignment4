from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .models import ModelResponse, ModelRunMetrics


class ModelUnavailableError(RuntimeError):
    pass


class ModelOutputError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout: int = 300):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _request(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if data is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelUnavailableError(
                f"Ollama is unavailable at {self.base_url}. Start Ollama and ensure {self.model} is downloaded."
            ) from exc

    def list_models(self) -> List[str]:
        payload = self._request("/api/tags")
        return [item.get("name", "") for item in payload.get("models", [])]

    def has_model(self) -> bool:
        target = self.model.split(":", 1)[0]
        return any(name == self.model or name.startswith(f"{target}:") for name in self.list_models())

    def _memory_snapshot(self) -> Dict[str, Optional[float]]:
        result: Dict[str, Optional[float]] = {
            "ollama_rss_mb": None,
            "model_size_mb": None,
            "model_vram_mb": None,
        }
        try:
            output = subprocess.run(
                ["ps", "-axo", "rss=,command="],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            rss_kb = sum(
                int(line.strip().split(None, 1)[0])
                for line in output.splitlines()
                if "ollama" in line.lower() and line.strip().split(None, 1)[0].isdigit()
            )
            if rss_kb:
                result["ollama_rss_mb"] = round(rss_kb / 1024, 2)
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
        try:
            payload = self._request("/api/ps")
            for item in payload.get("models", []):
                if item.get("name") == self.model or item.get("model") == self.model:
                    result["model_size_mb"] = round(float(item.get("size", 0)) / 1048576, 2)
                    result["model_vram_mb"] = round(float(item.get("size_vram", 0)) / 1048576, 2)
                    break
        except ModelUnavailableError:
            pass
        return result

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        num_predict: int,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> ModelResponse:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": "5m",
            "options": {
                "temperature": temperature,
                "num_ctx": 8192,
                "num_predict": num_predict,
            },
        }
        if response_schema is not None:
            payload["format"] = response_schema
        started = time.perf_counter()
        raw = self._request("/api/chat", payload)
        wall = time.perf_counter() - started
        memory = self._memory_snapshot()
        metrics = ModelRunMetrics(
            wall_seconds=round(wall, 3),
            total_duration_seconds=_nanos_to_seconds(raw.get("total_duration")),
            load_duration_seconds=_nanos_to_seconds(raw.get("load_duration")),
            prompt_tokens=raw.get("prompt_eval_count"),
            generated_tokens=raw.get("eval_count"),
            ollama_rss_mb=memory["ollama_rss_mb"],
            model_size_mb=memory["model_size_mb"],
            model_vram_mb=memory["model_vram_mb"],
        )
        content = raw.get("message", {}).get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ModelOutputError("Ollama returned an empty response")
        return ModelResponse(content=content.strip(), model=raw.get("model", self.model), raw=raw, metrics=metrics)


def _nanos_to_seconds(value: Any) -> Optional[float]:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value) / 1_000_000_000, 3)


def parse_json_object(text: str) -> Dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelOutputError(f"Model did not return valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ModelOutputError("Model response must be a JSON object")
    return value
