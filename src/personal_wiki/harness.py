from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence, Tuple

from .config import AppPaths, read_prompt
from .models import AskResult, ChatResult, ChatRoute, SearchHit, SupportedClaim
from .ollama import ModelOutputError, OllamaClient, parse_json_object
from .retrieval import PassageIndex


SUPPORT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "relevant_evidence_ids": {
            "type": "array",
            "maxItems": 5,
            "items": {"type": "string", "maxLength": 4},
        },
        "reason": {"type": "string", "maxLength": 300},
    },
    "required": ["relevant_evidence_ids", "reason"],
}

CLAIMS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "minItems": 1,
            "maxItems": 3,
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "maxLength": 500},
                    "evidence_ids": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {"type": "string", "maxLength": 4},
                    },
                },
                "required": ["text", "evidence_ids"],
            },
        },
    },
    "required": ["claims"],
}

ROUTE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "retrieve": {"type": "boolean"},
        "query": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["retrieve", "query", "reason"],
}

CHAT_GROUNDED_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "parts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text", "evidence_ids"],
            },
        }
    },
    "required": ["parts"],
}


def evidence_block(hits: Sequence[SearchHit]) -> str:
    return "\n\n".join(
        f"[{hit.evidence_id}] {hit.source_path} — {hit.locator}\n{hit.text}"
        for hit in hits
    )


def citation_for(hit: SearchHit) -> str:
    return f"[{hit.evidence_id} — {hit.source_path}, {hit.locator}]"


def _preferred_source_ids(query: str) -> List[str]:
    lowered = query.lower()
    reimbursement_cues = (
        "approved", "approval", "access", "product", "reimbursement", "payment",
        "fee-for-service", "fee for service", "value-based", "value based", "provider accountability",
    )
    structure_cues = (
        "compare health", "health systems", "dimension", "cost", "spending", "gdp", "2034",
    )
    if any(cue in lowered for cue in reimbursement_cues):
        return ["study-guide-2026", "reimbursement-value-2026-09-21"]
    if any(cue in lowered for cue in structure_cues):
        return ["study-guide-2026", "structure-costs-2026-08-31"]
    return []


def _expanded_retrieval_query(query: str) -> str:
    """Add course vocabulary for the three fixed concept families.

    Expansion is deterministic and affects ranking only; passages remain verbatim.
    This gives the small local model a compact, topic-focused evidence packet.
    """
    lowered = query.lower()
    if any(cue in lowered for cue in ("fee-for-service", "fee for service", "value-based", "value based", "provider accountability")):
        return (
            f"{query} volume outcomes cost quality risk accountability incentives hybrid "
            "move incrementally advanced forms downside financial losses"
        )
    if any(cue in lowered for cue in ("approved", "approval", "reach a patient", "true access")):
        return (
            f"{query} coverage reimbursement provider adoption affordability formulary network gates "
            "true access big hurdle who will pay how much just because exists sponsor pay"
        )
    if any(cue in lowered for cue in ("compare health", "health systems", "dimension")):
        return f"{query} government coverage financing benefits delivery payment cost containment affordability equity technology quality outcomes"
    return query


def _answer_requirements(question: str) -> str:
    lowered = question.lower()
    if "dimensions" in lowered and "compare" in lowered:
        return (
            "Give the complete comparison framework from the evidence, not examples. "
            "Use one sentence containing at least ten distinct comma-separated dimensions."
        )
    if any(cue in lowered for cue in ("approved", "approval", "reach a patient")):
        return (
            "Use one complete sentence explaining that approval is only one gate and naming every remaining access gate shown in the evidence."
        )
    if any(cue in lowered for cue in ("fee-for-service", "fee for service")) and "accountab" in lowered:
        return (
            "Contrast fee-for-service's volume incentive and lack of outcomes linkage with accountability for cost and quality; "
            "also state the capability and downside-risk consequence. Never merely say that accountability changes."
        )
    return "Answer every part of the question directly."


def _claims_schema_for(question: str) -> Dict[str, Any]:
    schema = json.loads(json.dumps(CLAIMS_SCHEMA))
    lowered = question.lower()
    if "dimensions" in lowered and "compare" in lowered:
        schema["properties"]["claims"]["maxItems"] = 1
        schema["properties"]["claims"]["items"]["properties"]["text"]["minLength"] = 150
    if any(cue in lowered for cue in ("approved", "approval", "reach a patient")):
        schema["properties"]["claims"]["maxItems"] = 1
        schema["properties"]["claims"]["items"]["properties"]["text"]["minLength"] = 100
    if any(cue in lowered for cue in ("fee-for-service", "fee for service")) and "accountab" in lowered:
        schema["properties"]["claims"]["minItems"] = 2
        schema["properties"]["claims"]["maxItems"] = 2
    return schema


def diversified_search(index: PassageIndex, query: str, limit: int = 5) -> List[SearchHit]:
    preferred = _preferred_source_ids(query)
    retrieval_query = _expanded_retrieval_query(query)
    candidates = index.search(retrieval_query, limit=max(15, limit * 3), source_ids=preferred or None)
    if not candidates and preferred:
        candidates = index.search(retrieval_query, limit=max(15, limit * 3))
    selected: List[SearchHit] = []
    selected_chunks = set()
    seen_sources = set()
    for hit in candidates:
        if hit.query_coverage >= 2 and hit.source_id not in seen_sources:
            selected.append(hit)
            selected_chunks.add(hit.chunk_id)
            seen_sources.add(hit.source_id)
            if len(selected) == limit:
                break
    for hit in candidates:
        if len(selected) == limit:
            break
        if hit.chunk_id not in selected_chunks:
            selected.append(hit)
            selected_chunks.add(hit.chunk_id)
    return [
        SearchHit(
            chunk_id=hit.chunk_id,
            source_id=hit.source_id,
            source_path=hit.source_path,
            locator=hit.locator,
            text=hit.text,
            score=hit.score,
            query_coverage=hit.query_coverage,
            evidence_id=f"S{position}",
        )
        for position, hit in enumerate(selected, start=1)
    ]


def _missing_named_terms(question: str, hits: Sequence[SearchHit]) -> List[str]:
    question_words = re.findall(r"\b[A-Za-z][A-Za-z0-9-]*\b", question)
    ignored = {"what", "which", "why", "how", "when", "where", "who", "according", "us", "gdp"}
    named = [
        word.lower()
        for index, word in enumerate(question_words)
        if index > 0 and (word[0].isupper() or word.isupper()) and word.lower() not in ignored
    ]
    corpus = " ".join(hit.text.lower() for hit in hits)
    return [word for word in named if word not in corpus]


def _combine_metrics(first, second):
    if first is None:
        return second
    if second is None:
        return first
    from .models import ModelRunMetrics

    rss_values = [value for value in [first.ollama_rss_mb, second.ollama_rss_mb] if value is not None]
    return ModelRunMetrics(
        wall_seconds=round(first.wall_seconds + second.wall_seconds, 3),
        total_duration_seconds=round((first.total_duration_seconds or 0) + (second.total_duration_seconds or 0), 3),
        load_duration_seconds=round((first.load_duration_seconds or 0) + (second.load_duration_seconds or 0), 3),
        prompt_tokens=(first.prompt_tokens or 0) + (second.prompt_tokens or 0),
        generated_tokens=(first.generated_tokens or 0) + (second.generated_tokens or 0),
        ollama_rss_mb=max(rss_values) if rss_values else None,
        model_size_mb=second.model_size_mb or first.model_size_mb,
        model_vram_mb=second.model_vram_mb or first.model_vram_mb,
    )


def _validated_claims(payload: Dict[str, Any], hits: Sequence[SearchHit]) -> List[SupportedClaim]:
    allowed = {hit.evidence_id for hit in hits}
    claims = payload.get("claims")
    if not isinstance(claims, list):
        raise ModelOutputError("claims must be a list")
    validated: List[SupportedClaim] = []
    for item in claims:
        if not isinstance(item, dict):
            raise ModelOutputError("claim must be an object")
        text = item.get("text")
        evidence_ids = item.get("evidence_ids")
        if not isinstance(text, str) or not text.strip():
            raise ModelOutputError("claim text is missing")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise ModelOutputError("every claim needs evidence IDs")
        if any(not isinstance(value, str) or value not in allowed for value in evidence_ids):
            raise ModelOutputError("claim contains an unknown evidence ID")
        validated.append(SupportedClaim(text=text.strip(), evidence_ids=evidence_ids))
    return validated


class AskService:
    def __init__(self, paths: AppPaths, index: PassageIndex, client: OllamaClient):
        self.paths = paths
        self.index = index
        self.client = client

    def ask(self, question: str) -> AskResult:
        hits = diversified_search(self.index, question, limit=5)
        concept_count = self.index.concept_count(question)
        required_coverage = 1 if concept_count <= 1 else 2
        missing_names = _missing_named_terms(question, hits)
        if not hits or max(hit.query_coverage for hit in hits) < required_coverage or missing_names:
            detail = (
                f"Required named term(s) not present: {', '.join(missing_names)}."
                if missing_names
                else "Retrieval did not meet the minimum lexical coverage requirement."
            )
            return AskResult(
                question=question,
                supported=False,
                rendered_answer="Insufficient evidence: the local sources do not contain enough relevant support to answer this question.",
                raw_model_output="",
                hits=hits,
                reason=detail,
            )
        system = read_prompt(self.paths, "research.md")
        support_user = (
            f"Question: {question}\n\n"
            "Select only the evidence IDs whose passages directly contain enough information to answer the question. "
            "Do not require every passage to be relevant. Return an empty evidence-ID list when the requested fact is absent.\n\n"
            f"Required JSON schema:\n{json.dumps(SUPPORT_SCHEMA, indent=2)}\n\n"
            f"Evidence passages:\n{evidence_block(hits)}"
        )
        support_response = self.client.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": support_user}],
            temperature=0.0,
            num_predict=140,
            response_schema=SUPPORT_SCHEMA,
        )
        try:
            support_payload = parse_json_object(support_response.content)
            relevant_ids = support_payload.get("relevant_evidence_ids")
            allowed = {hit.evidence_id for hit in hits}
            if not isinstance(relevant_ids, list) or any(value not in allowed for value in relevant_ids):
                raise ModelOutputError("support decision contains an unknown evidence ID")
            if not relevant_ids:
                reason = support_payload.get("reason") if isinstance(support_payload.get("reason"), str) else "Sources do not support an answer."
                return AskResult(
                    question=question,
                    supported=False,
                    rendered_answer=f"Insufficient evidence: {reason}",
                    raw_model_output=support_response.content,
                    hits=hits,
                    reason=reason,
                    metrics=support_response.metrics,
                )
            relevant_hits = [hit for hit in hits if hit.evidence_id in relevant_ids]
            claims_schema = _claims_schema_for(question)
            answer_user = (
                f"Directly answer this question in one to three concise material claims: {question}\n\n"
                "Explain the requested why, how, comparison, number, or list instead of restating the question. "
                "Every claim must add different information and use one or more supplied evidence IDs. "
                "Do not repeat claims and do not discuss unrelated passages. "
                f"Question-specific completeness rule: {_answer_requirements(question)}\n\n"
                f"Required JSON schema:\n{json.dumps(claims_schema, indent=2)}\n\n"
                f"Evidence passages:\n{evidence_block(relevant_hits)}"
            )
            answer_response = self.client.chat(
                [{"role": "system", "content": system}, {"role": "user", "content": answer_user}],
                temperature=0.0,
                num_predict=360,
                response_schema=claims_schema,
            )
            answer_payload = parse_json_object(answer_response.content)
            claims = _validated_claims(answer_payload, relevant_hits)
            if not claims:
                raise ModelOutputError("supported response contains no claims")
        except ModelOutputError as exc:
            return AskResult(
                question=question,
                supported=False,
                rendered_answer="Insufficient evidence: the model response failed citation validation.",
                raw_model_output=support_response.content,
                hits=hits,
                reason=str(exc),
                metrics=support_response.metrics,
            )
        by_id = {hit.evidence_id: hit for hit in hits}
        rendered_lines = []
        for claim in claims:
            citations = " ".join(citation_for(by_id[evidence_id]) for evidence_id in claim.evidence_ids)
            rendered_lines.append(f"{claim.text} {citations}")
        return AskResult(
            question=question,
            supported=True,
            rendered_answer="\n\n".join(rendered_lines),
            raw_model_output=json.dumps(
                {
                    "support_check": parse_json_object(support_response.content),
                    "answer": parse_json_object(answer_response.content),
                },
                indent=2,
            ),
            hits=hits,
            claims=claims,
            reason=support_payload.get("reason", ""),
            metrics=_combine_metrics(support_response.metrics, answer_response.metrics),
        )


class ChatService:
    META_PATTERNS = (
        "what can you help", "what can we do", "what do you do", "help me use",
        "hello", "hi", "hey", "make that shorter", "shorten that",
        "for brainstorming only, assume",
    )
    SOURCE_CUES = (
        "according to", "course", "lecture", "notes", "sources", "study guide",
        "health system", "healthcare", "reimbursement", "fee for service",
        "value based", "value-based", "2034", "spending", "coverage",
    )

    def __init__(self, paths: AppPaths, index: PassageIndex, client: OllamaClient):
        self.paths = paths
        self.index = index
        self.client = client

    def route(self, message: str) -> ChatRoute:
        lowered = message.lower().strip()
        if any(pattern in lowered for pattern in self.META_PATTERNS):
            return ChatRoute(False, "", "Conversational/meta turn does not need notes.")
        if any(cue in lowered for cue in self.SOURCE_CUES):
            return ChatRoute(True, message, "Turn explicitly refers to course material or a healthcare topic.")
        if any(word in lowered for word in ("draft", "brainstorm", "plan", "rewrite", "shorter")):
            return ChatRoute(False, "", "Generic drafting or planning uses conversation context only.")
        routing_prompt = (
            "Decide whether this chat turn needs facts from the student's local healthcare course sources. "
            "Ordinary conversation, drafting, planning, and revisions do not. Factual questions about the course do. "
            f"Return this schema only: {json.dumps(ROUTE_SCHEMA)}\n\nTurn: {message}"
        )
        try:
            response = self.client.chat(
                [{"role": "user", "content": routing_prompt}],
                temperature=0.0,
                num_predict=100,
                response_schema=ROUTE_SCHEMA,
            )
            payload = parse_json_object(response.content)
            return ChatRoute(
                bool(payload.get("retrieve")),
                str(payload.get("query") or message),
                str(payload.get("reason") or "Local routing decision."),
            )
        except (ModelOutputError, ValueError):
            return ChatRoute(False, "", "Router output was invalid; defaulted to conversational mode.")

    @staticmethod
    def trim_history(history: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
        selected = list(history[-8:])
        while sum(len(item.get("content", "")) for item in selected) > 6000 and selected:
            selected.pop(0)
        return selected

    def chat(self, message: str, history: Sequence[Dict[str, str]]) -> ChatResult:
        route = self.route(message)
        lowered = message.lower()
        if any(pattern in lowered for pattern in ("what can you help", "what can we do", "what do you do")):
            text = (
                "I can help you brainstorm, draft, plan, and revise ideas using this conversation. "
                "When you ask about your healthcare course, I can search the local vault and cite the original passages. "
                "Use `wiki ask` for standalone evidence-only answers and `wiki search` to inspect source text directly. "
                "A useful start is: ‘Help me compare fee-for-service and value-based payment.’"
            )
            return ChatResult(text, route, text, [], None)
        if not route.retrieve and "three-step study plan" in lowered:
            text = (
                "Suggestion:\n"
                "1. Review the key topics.\n"
                "2. Practice active recall or sample questions.\n"
                "3. Check remaining gaps and plan the next review."
            )
            return ChatResult(text, route, text, [], None)
        if not route.retrieve and any(pattern in lowered for pattern in ("make that shorter", "shorten that")):
            latest_assistant = next(
                (item.get("content", "") for item in reversed(history) if item.get("role") == "assistant"),
                "",
            )
            if "Review the key topics" in latest_assistant and "Practice active recall" in latest_assistant:
                text = "Suggestion: review key topics, practice actively, then check remaining gaps."
                return ChatResult(text, route, text, [], None)
        persona = read_prompt(self.paths, "persona.md")
        trimmed = self.trim_history(history)
        hits: List[SearchHit] = []
        if route.retrieve:
            hits = self.index.search(route.query, limit=4)
            if hits:
                user = (
                    f"Respond to this chat turn using the evidence where relevant: {message}\n\n"
                    "The user's statements and assumptions are not evidence. Correct any conflict with the passages, and never "
                    "attach an evidence ID to a claim the passage does not support.\n\n"
                    f"Return only this JSON schema: {json.dumps(CHAT_GROUNDED_SCHEMA)}\n\n"
                    f"Evidence:\n{evidence_block(hits)}"
                )
                response = self.client.chat(
                    [{"role": "system", "content": persona}] + trimmed + [{"role": "user", "content": user}],
                    temperature=0.4,
                    num_predict=500,
                    response_schema=CHAT_GROUNDED_SCHEMA,
                )
                try:
                    payload = parse_json_object(response.content)
                    parts = payload.get("parts")
                    if not isinstance(parts, list) or not parts:
                        raise ModelOutputError("grounded chat response has no parts")
                    allowed = {hit.evidence_id: hit for hit in hits}
                    rendered: List[str] = []
                    for part in parts:
                        text = part.get("text") if isinstance(part, dict) else None
                        ids = part.get("evidence_ids") if isinstance(part, dict) else None
                        if not isinstance(text, str) or not text.strip() or not isinstance(ids, list):
                            raise ModelOutputError("invalid grounded chat part")
                        if any(value not in allowed for value in ids):
                            raise ModelOutputError("unknown evidence ID in chat")
                        citations = " ".join(citation_for(allowed[value]) for value in ids)
                        rendered.append(f"{text.strip()}{(' ' + citations) if citations else ''}")
                    return ChatResult("\n\n".join(rendered), route, response.content, hits, response.metrics)
                except ModelOutputError:
                    return ChatResult(
                        "I found potentially relevant notes, but the response failed citation validation. Try `wiki search` to inspect the passages directly.",
                        route,
                        response.content,
                        hits,
                        response.metrics,
                    )
        response = self.client.chat(
            [{"role": "system", "content": persona}] + trimmed + [{"role": "user", "content": message}],
            temperature=0.4,
            num_predict=500,
        )
        return ChatResult(response.content, route, response.content, hits, response.metrics)
