from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

from .config import AppPaths
from .doctor import doctor_snapshot
from .harness import AskService, ChatService
from .models import AskResult, ChatResult, SearchHit
from .ollama import OllamaClient
from .retrieval import PassageIndex


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _format_hits(hits: Sequence[SearchHit]) -> str:
    if not hits:
        return "_No passages retrieved._"
    sections = []
    for hit in hits:
        sections.append(
            f"### {hit.evidence_id}: `{hit.source_path}` — {hit.locator}\n\n"
            f"Score: `{hit.score:.6f}`; query coverage: `{hit.query_coverage}`\n\n"
            f"> {hit.text.replace(chr(10), chr(10) + '> ')}"
        )
    return "\n\n".join(sections)


def write_ask_card(
    path: Path,
    case: Dict[str, Any],
    result: AskResult,
    model: str,
    offline: bool,
) -> None:
    expected_sources = case.get("expected_sources", [])
    retrieved_sources = sorted({hit.source_id for hit in result.hits})
    expected_supported = bool(expected_sources)
    structural_pass = result.supported == expected_supported
    if expected_supported:
        structural_pass = structural_pass and all(source in retrieved_sources for source in expected_sources)
    assessment = "PASS" if structural_pass else "REVIEW NEEDED"
    metrics = result.metrics.to_dict() if result.metrics else {}
    content = f"""# {case['id']} Evidence Card

- Captured: `{_now()}`
- Mode: `ask`
- Execution: `local`
- Offline flag: `{str(offline).lower()}`
- Model: `{model}`
- Expected behavior: {case['expected_behavior']}
- Expected sources: `{json.dumps(expected_sources)}`
- Expected locators: `{json.dumps(case.get('expected_locators', []))}`

## Question

{case['question']}

## Retrieved Original Passages

{_format_hits(result.hits)}

## Actual Displayed Answer

{result.rendered_answer}

## Raw Gemma Output

```json
{result.raw_model_output or '(model was not called because retrieval was insufficient)'}
```

## Run Metrics

```json
{json.dumps(metrics, indent=2, sort_keys=True)}
```

## Assessment

- Automated structural assessment: **{assessment}**
- Retrieved source IDs: `{json.dumps(retrieved_sources)}`
- Citation validation: `{'passed' if result.supported else 'not applicable or insufficient evidence'}`
- Human claim-to-passage review: `pending final review`
- Notes: {result.reason or 'No additional limitation reported.'}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _chat_entry(prompt: str, result: ChatResult) -> str:
    return (
        f"### User\n\n{prompt}\n\n"
        f"### Assistant\n\n{result.text}\n\n"
        f"- Retrieval used: `{str(result.route.retrieve).lower()}`\n"
        f"- Routing reason: {result.route.reason}\n"
    )


class EvalRunner:
    def __init__(
        self,
        paths: AppPaths,
        index: PassageIndex,
        client: OllamaClient,
        ask: AskService,
        chat: ChatService,
    ):
        self.paths = paths
        self.index = index
        self.client = client
        self.ask_service = ask
        self.chat_service = chat

    def run(self, *, offline: bool) -> Dict[str, Any]:
        config = json.loads((self.paths.root / "evals" / "questions.json").read_text(encoding="utf-8"))
        doctor = doctor_snapshot(self.paths, self.index, self.client, offline_requested=offline)
        if offline and doctor.get("offline_confirmed") is not True:
            raise ValueError("Offline evaluation refused: Wi-Fi is not confirmed off by `wiki doctor --offline`.")
        offline_path = self.paths.evidence / "offline" / "doctor.json"
        offline_path.parent.mkdir(parents=True, exist_ok=True)
        offline_path.write_text(json.dumps(doctor, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        ask_results = []
        for case in config["questions"]:
            result = self.ask_service.ask(case["question"])
            write_ask_card(
                self.paths.evidence / "ask" / f"{case['id']}.md",
                case,
                result,
                self.client.model,
                offline,
            )
            ask_results.append({"id": case["id"], "supported": result.supported})

        search_hits = self.index.search(config["search_check"], limit=5)
        history: List[Dict[str, str]] = []
        transcript_parts = [
            "# Chat and Search Mode Checks",
            "",
            f"- Captured: `{_now()}`",
            "- Execution: `local`",
            f"- Offline flag: `{str(offline).lower()}`",
            f"- Model: `{self.client.model}`",
            "",
            "## Chat Checks",
            "",
        ]
        chat_results: List[ChatResult] = []
        for prompt in config["chat_checks"]:
            result = self.chat_service.chat(prompt, history)
            chat_results.append(result)
            transcript_parts.append(_chat_entry(prompt, result))
            history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": result.text}])

        transcript_parts.extend(
            [
                "## Raw Search Check",
                "",
                f"Query: `{config['search_check']}`",
                "",
                _format_hits(search_hits),
                "",
                "The search path stopped after retrieval; no language-model answer was generated.",
                "",
                "## Ask Ignores Chat History",
                "",
            ]
        )
        separated = self.ask_service.ask(config["history_separation_ask"])
        transcript_parts.extend(
            [
                f"Question: {config['history_separation_ask']}",
                "",
                separated.rendered_answer,
                "",
                "This ask call received no chat-history argument; its citations come only from the local index.",
                "",
                "## Assessment",
                "",
                "- Capability chat accurately explained the real commands: `" + str("wiki ask" in chat_results[0].text and "wiki search" in chat_results[0].text).lower() + "`",
                "- Capability chat avoided retrieval: `" + str(not chat_results[0].route.retrieve).lower() + "`",
                "- Follow-up used conversation without retrieval: `" + str(not chat_results[2].route.retrieve).lower() + "`",
                "- Hypothetical assumption stayed outside the evidence store: `" + str(not chat_results[3].route.retrieve).lower() + "`",
                "- Search generated no synthesized answer: `true`",
                "- Human review: `pending final review`",
            ]
        )
        (self.paths.evidence / "mode-checks.md").write_text("\n".join(transcript_parts), encoding="utf-8")
        return {
            "ask_results": ask_results,
            "search_hit_count": len(search_hits),
            "mode_checks": "evidence/mode-checks.md",
            "doctor": "evidence/offline/doctor.json",
        }
