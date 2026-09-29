from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from .config import AppPaths, load_page_specs, load_sources, read_prompt
from .models import ModelRunMetrics, SearchHit, WikiPageSpec
from .ollama import ModelOutputError, OllamaClient, parse_json_object
from .retrieval import PassageIndex


INGEST_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "maxLength": 700},
        "details": {
            "type": "array",
            "minItems": 2,
            "maxItems": 4,
            "items": {
                "type": "object",
                "properties": {
                    "heading": {"type": "string", "maxLength": 80},
                    "paragraph": {"type": "string", "maxLength": 900},
                },
                "required": ["heading", "paragraph"],
            },
        },
        "limitations": {"type": "string", "maxLength": 500},
    },
    "required": ["summary", "details", "limitations"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 1, "pages": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_state(path: Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_page_specs(specs: Sequence[WikiPageSpec]) -> List[str]:
    errors: List[str] = []
    titles = {spec.title for spec in specs}
    paths = set()
    for spec in specs:
        word_count = len(spec.title.split())
        if not 2 <= word_count <= 6:
            errors.append(f"{spec.title}: title must contain 2-6 words")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 '&-]*", spec.title):
            errors.append(f"{spec.title}: title contains unsupported characters")
        if str(spec.relative_path) in paths:
            errors.append(f"Duplicate path: {spec.relative_path}")
        paths.add(str(spec.relative_path))
        for related in spec.related:
            if related.get("title") not in titles:
                errors.append(f"{spec.title}: missing related target {related.get('title')}")
            if not related.get("reason", "").strip():
                errors.append(f"{spec.title}: related link needs a reason")
    return errors


def _fingerprint(spec: WikiPageSpec, source_hashes: Dict[str, str]) -> str:
    payload = {
        "spec": asdict(spec),
        "source_hashes": {source_id: source_hashes[source_id] for source_id in spec.source_ids},
        "prompt_version": 1,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _collect_hits(index: PassageIndex, spec: WikiPageSpec) -> List[SearchHit]:
    gathered: List[SearchHit] = []
    seen = set()
    for source_id in spec.source_ids:
        for hit in index.search(spec.focus_query, limit=4, source_ids=[source_id]):
            if hit.chunk_id not in seen:
                seen.add(hit.chunk_id)
                gathered.append(hit)
    return [
        SearchHit(
            chunk_id=hit.chunk_id,
            source_id=hit.source_id,
            source_path=hit.source_path,
            locator=hit.locator,
            text=hit.text,
            score=hit.score,
            query_coverage=hit.query_coverage,
            evidence_id=f"S{index_number}",
        )
        for index_number, hit in enumerate(gathered, start=1)
    ]


def _evidence_text(hits: Sequence[SearchHit]) -> str:
    return "\n\n".join(
        f"[{hit.evidence_id}] {hit.source_path} — {hit.locator}\n{hit.text}"
        for hit in hits
    )


def _validate_generated(payload: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]], str]:
    summary = payload.get("summary")
    details = payload.get("details")
    limitations = payload.get("limitations")
    if not isinstance(summary, str) or not summary.strip():
        raise ModelOutputError("Generated page is missing a summary")
    if not isinstance(details, list) or not 2 <= len(details) <= 4:
        raise ModelOutputError("Generated page must contain two to four detail sections")
    cleaned: List[Dict[str, str]] = []
    for detail in details:
        if not isinstance(detail, dict):
            raise ModelOutputError("Generated detail must be an object")
        heading = detail.get("heading")
        paragraph = detail.get("paragraph")
        if not isinstance(heading, str) or not heading.strip():
            raise ModelOutputError("Generated detail is missing a heading")
        if not isinstance(paragraph, str) or not paragraph.strip():
            raise ModelOutputError("Generated detail is missing a paragraph")
        cleaned.append({"heading": heading.strip(), "paragraph": paragraph.strip()})
    return summary.strip(), cleaned, limitations.strip() if isinstance(limitations, str) else ""


def _render_page(
    paths: AppPaths,
    spec: WikiPageSpec,
    summary: str,
    details: Sequence[Dict[str, str]],
    limitations: str,
    hits: Sequence[SearchHit],
    model: str,
    review_status: str,
) -> str:
    source_catalog = {item.source_id: item for item in load_sources(paths)}
    source_locators: Dict[str, List[str]] = {}
    for hit in hits:
        source_locators.setdefault(hit.source_id, [])
        if hit.locator not in source_locators[hit.source_id]:
            source_locators[hit.source_id].append(hit.locator)

    lines = [
        "---",
        f"page_id: {spec.page_id}",
        f"review_status: {review_status}",
        f"generated_model: {model}",
        f"generated_at: {_now()}",
        "source_ids:",
    ]
    lines.extend(f"  - {source_id}" for source_id in spec.source_ids)
    lines.extend(["---", "", f"# {spec.title}", "", "## Summary", "", summary, ""])
    for detail in details:
        lines.extend([f"## {detail['heading']}", "", detail["paragraph"], ""])
    if limitations:
        lines.extend(["## Limits of These Sources", "", limitations, ""])
    lines.extend(["## Related Notes", ""])
    for related in spec.related:
        lines.append(f"- [[{related['title']}]] — {related['reason']}")
    lines.extend(["", "## Sources", ""])
    page_path = paths.vault / spec.relative_path
    for source_id in spec.source_ids:
        source = source_catalog[source_id]
        relative = os.path.relpath(paths.root / source.path, start=page_path.parent)
        locators = ", ".join(source_locators.get(source_id, [])) or "source document"
        lines.append(f"- [{source.title}](<{relative}>) — {locators}")
    lines.append("")
    return "\n".join(lines)


class WikiPageService:
    def __init__(self, paths: AppPaths, passage_index: PassageIndex, client: OllamaClient):
        self.paths = paths
        self.index = passage_index
        self.client = client

    def generate_all(self) -> Dict[str, Any]:
        specs = load_page_specs(self.paths)
        errors = validate_page_specs(specs)
        if errors:
            raise ValueError("Invalid wiki page configuration:\n" + "\n".join(errors))
        sources = load_sources(self.paths)
        source_hashes = {source.source_id: source.sha256 for source in sources}
        state = _load_state(self.paths.generation_state)
        state.setdefault("pages", {})
        prompt = read_prompt(self.paths, "ingest.md")
        results: Dict[str, Any] = {"generated": [], "skipped": [], "drafted": [], "metrics": {}}

        for spec in specs:
            destination = self.paths.vault / spec.relative_path
            fingerprint = _fingerprint(spec, source_hashes)
            previous = state["pages"].get(spec.page_id, {})
            if destination.exists() and previous.get("fingerprint") == fingerprint:
                results["skipped"].append(spec.title)
                continue
            hits = _collect_hits(self.index, spec)
            if not hits:
                raise ValueError(f"No source passages found for {spec.title}")
            user_prompt = (
                f"Create the body for the wiki page titled '{spec.title}'.\n\n"
                "Keep the summary under 90 words. Use exactly 2 or 3 detail sections, each with a heading "
                "under 8 words and a paragraph under 110 words. Keep limitations under 60 words.\n\n"
                f"Required JSON schema:\n{json.dumps(INGEST_SCHEMA, indent=2)}\n\n"
                f"Evidence:\n{_evidence_text(hits)}"
            )
            response = self.client.chat(
                [{"role": "system", "content": prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                num_predict=900,
                response_schema=INGEST_SCHEMA,
            )
            try:
                summary, details, limitations = _validate_generated(parse_json_object(response.content))
            except ModelOutputError:
                retry_prompt = (
                    user_prompt
                    + "\n\nYour previous response was invalid or truncated. Return a shorter complete JSON object now; "
                    "do not include markdown fences or any text outside the object."
                )
                response = self.client.chat(
                    [{"role": "system", "content": prompt}, {"role": "user", "content": retry_prompt}],
                    temperature=0.0,
                    num_predict=1100,
                    response_schema=INGEST_SCHEMA,
                )
                summary, details, limitations = _validate_generated(parse_json_object(response.content))
            rendered = _render_page(
                self.paths,
                spec,
                summary,
                details,
                limitations,
                hits,
                response.model,
                "pending",
            )
            status = previous.get("status")
            if destination.exists() and status == "reviewed":
                draft = self.paths.data / "drafts" / f"{spec.page_id}.md"
                draft.parent.mkdir(parents=True, exist_ok=True)
                draft.write_text(rendered, encoding="utf-8")
                results["drafted"].append(spec.title)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(rendered, encoding="utf-8")
                state["pages"][spec.page_id] = {
                    "title": spec.title,
                    "path": str(spec.relative_path),
                    "fingerprint": fingerprint,
                    "status": "pending",
                    "updated_at": _now(),
                    "model": response.model,
                }
                results["generated"].append(spec.title)
            results["metrics"][spec.page_id] = response.metrics.to_dict()
            _save_state(self.paths.generation_state, state)

        rebuild_vault_index(self.paths)
        return results


def review_pages(
    paths: AppPaths,
    *,
    approve_title: str = "",
    approve_all: bool = False,
    show_title: str = "",
) -> Dict[str, Any]:
    specs = load_page_specs(paths)
    state = _load_state(paths.generation_state)
    pages = state.setdefault("pages", {})
    by_title = {spec.title.lower(): spec for spec in specs}

    if show_title:
        spec = by_title.get(show_title.lower())
        if not spec:
            raise ValueError(f"Unknown page title: {show_title}")
        path = paths.vault / spec.relative_path
        if not path.exists():
            raise FileNotFoundError(f"Page has not been generated: {spec.title}")
        return {"show": path.read_text(encoding="utf-8"), "path": str(path)}

    targets: List[WikiPageSpec] = []
    if approve_all:
        targets = [spec for spec in specs if pages.get(spec.page_id, {}).get("status") == "pending"]
    elif approve_title:
        spec = by_title.get(approve_title.lower())
        if not spec:
            raise ValueError(f"Unknown page title: {approve_title}")
        targets = [spec]

    approved: List[str] = []
    for spec in targets:
        path = paths.vault / spec.relative_path
        if not path.exists():
            raise FileNotFoundError(f"Page has not been generated: {spec.title}")
        content = path.read_text(encoding="utf-8")
        if "review_status: pending" in content:
            content = content.replace("review_status: pending", "review_status: reviewed", 1)
            path.write_text(content, encoding="utf-8")
        pages.setdefault(spec.page_id, {})["status"] = "reviewed"
        pages[spec.page_id]["reviewed_at"] = _now()
        approved.append(spec.title)
    if approved:
        _save_state(paths.generation_state, state)
        rebuild_vault_index(paths)

    listing = [
        {
            "title": spec.title,
            "status": pages.get(spec.page_id, {}).get("status", "not generated"),
            "path": str(spec.relative_path),
        }
        for spec in specs
    ]
    return {"approved": approved, "pages": listing}


def rebuild_vault_index(paths: AppPaths) -> None:
    specs = load_page_specs(paths)
    state = _load_state(paths.generation_state)
    reviewed = {
        page_id
        for page_id, value in state.get("pages", {}).items()
        if value.get("status") == "reviewed"
    }
    grouped: Dict[str, List[WikiPageSpec]] = {}
    for spec in specs:
        if spec.page_id in reviewed and (paths.vault / spec.relative_path).exists():
            grouped.setdefault(spec.folder, []).append(spec)
    lines = [
        "# Healthcare Personal Wiki",
        "",
        "A reviewed map of healthcare-system structure, costs, reimbursement, and payment incentives. Original files remain unchanged in `raw/`; generated and reviewed notes live in `wiki/`.",
        "",
    ]
    for folder in ["Systems", "Concepts"]:
        lines.extend([f"## {folder}", ""])
        entries = grouped.get(folder, [])
        if not entries:
            lines.extend(["_No reviewed pages yet._", ""])
            continue
        for spec in entries:
            summary = {
                "Healthcare System Structure": "Actors, financing, coverage, and accountability across health systems.",
                "Healthcare Costs and Value": "Why spending and outcomes must be interpreted through explicit tradeoffs.",
                "Reimbursement and Access": "How coverage and payment determine whether products and services reach patients.",
                "Fee for Service": "The dominant volume-based payment baseline and its incentives.",
                "Value Based Payment": "Models that add quality, savings, risk, and population accountability.",
            }[spec.title]
            lines.append(f"- [[{spec.title}]] — {summary}")
        lines.append("")
    paths.vault.mkdir(parents=True, exist_ok=True)
    (paths.vault / "index.md").write_text("\n".join(lines), encoding="utf-8")


def validate_wiki(paths: AppPaths) -> List[str]:
    errors: List[str] = []
    specs = load_page_specs(paths)
    titles = {spec.title for spec in specs}
    for spec in specs:
        path = paths.vault / spec.relative_path
        if not path.exists():
            errors.append(f"Missing wiki page: {spec.relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        first_heading = next((line[2:] for line in text.splitlines() if line.startswith("# ")), "")
        if first_heading != spec.title or path.stem != spec.title:
            errors.append(f"Heading/filename mismatch: {spec.relative_path}")
        links = re.findall(r"\[\[([^\]|]+)", text)
        for link in links:
            if link not in titles:
                errors.append(f"Broken internal link in {spec.title}: {link}")
    return errors
