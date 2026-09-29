from __future__ import annotations

import json
import platform
import shutil
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from .config import AppPaths, load_sources
from .extractors import sha256_file
from .ollama import ModelUnavailableError, OllamaClient
from .retrieval import PassageIndex
from .wiki_pages import validate_wiki


def _run(command):
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _hardware() -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "os": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
    }
    raw = _run(["system_profiler", "SPHardwareDataType", "-json"])
    if raw:
        try:
            items = json.loads(raw).get("SPHardwareDataType", [])
            if items:
                item = items[0]
                payload.update(
                    {
                        "model_name": item.get("machine_name"),
                        "model_identifier": item.get("machine_model"),
                        "chip": item.get("chip_type"),
                        "memory": item.get("physical_memory"),
                        "cores": item.get("number_processors"),
                    }
                )
        except json.JSONDecodeError:
            pass
    disk = shutil.disk_usage(Path.cwd())
    payload["free_disk_gib"] = round(disk.free / (1024 ** 3), 2)
    return payload


def _wifi_status() -> Dict[str, Any]:
    ports = _run(["networksetup", "-listallhardwareports"])
    device: Optional[str] = None
    lines = ports.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "Hardware Port: Wi-Fi" and index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if next_line.startswith("Device:"):
                device = next_line.split(":", 1)[1].strip()
                break
    if not device:
        device = "en0"
    status = _run(["networksetup", "-getairportpower", device])
    return {
        "wifi_device": device,
        "wifi_status": status or "unavailable",
        "wifi_off": status.lower().endswith("off") if status else None,
    }


def doctor_snapshot(
    paths: AppPaths,
    index: PassageIndex,
    client: OllamaClient,
    *,
    offline_requested: bool,
) -> Dict[str, Any]:
    source_checks = []
    for source in load_sources(paths):
        source_path = paths.root / source.path
        actual = sha256_file(source_path) if source_path.exists() else None
        source_checks.append(
            {
                "source_id": source.source_id,
                "path": source.path,
                "exists": source_path.exists(),
                "expected_sha256": source.sha256,
                "actual_sha256": actual,
                "hash_matches": actual == source.sha256,
            }
        )
    try:
        models = client.list_models()
        ollama_available = True
    except ModelUnavailableError:
        models = []
        ollama_available = False
    exact_model_installed = any(name == client.model for name in models)
    wifi = _wifi_status()
    snapshot = {
        "mode": "doctor",
        "execution": "local",
        "offline_requested": offline_requested,
        "offline_confirmed": wifi["wifi_off"] is True if offline_requested else None,
        "network": wifi,
        "hardware": _hardware(),
        "sqlite_version": sqlite3.sqlite_version,
        "fts5_passage_count": index.count(),
        "ollama_available": ollama_available,
        "model": client.model,
        "exact_model_installed": exact_model_installed,
        "installed_models": models,
        "sources": source_checks,
        "wiki_validation_errors": validate_wiki(paths),
    }
    snapshot["required_checks_pass"] = (
        all(item["hash_matches"] for item in source_checks)
        and index.count() > 0
        and ollama_available
        and exact_model_installed
        and not snapshot["wiki_validation_errors"]
        and (not offline_requested or snapshot["offline_confirmed"] is True)
    )
    return snapshot
