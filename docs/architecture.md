# Architecture and Trust Boundaries

## Data Flow

```text
vault/raw files
      │ hash validation against committed catalog
      ▼
PDF/DOCX extraction ──► original Passage records ──► SQLite FTS5
                                                   │
                         ┌─────────────────────────┼────────────────────────┐
                         ▼                         ▼                        ▼
                    raw search               standalone ask          routed chat
                    no model                 no chat history         recent history
                                                   │                        │
                                                   └──── local Ollama ──────┘
                                                            │
                                      schema + evidence-ID validation
                                                            │
                                      deterministic citation renderer

FTS5 passages ──► local Gemma page fields ──► deterministic Markdown harness
                                                    │
                                      pending review / external draft
                                                    │
                                             reviewed wiki index
```

## Explicit Records

The main data contracts are dataclasses in [`src/personal_wiki/models.py`](../src/personal_wiki/models.py):

- `SourceRecord`: immutable catalog identity, path, hash, type, attribution, provenance, and permission.
- `Passage`: original extracted text with slide or section locator.
- `SearchHit`: ranked passage plus query coverage and renderer-controlled evidence ID.
- `WikiPageSpec`: stable page title, folder, focus, source IDs, and related-note reasons.
- `ChatRoute`: retrieval decision, query, and reason.
- `SupportedClaim`: generated text plus validated evidence IDs.
- `ModelRunMetrics`: wall time, Ollama durations, token counts, process memory, and model allocation.

## Storage Boundary

The Obsidian vault contains only source files, reviewed notes, and the grouped index. Rebuildable and sensitive workflow state stays outside it:

- `data/index.sqlite3`: ignored SQLite index.
- `data/drafts/`: ignored staged revisions for changed sources.
- `data/runtime/`: ignored latest-run state.
- `evidence/`: committed evaluation outputs and screenshots, but no private answer key.

The three raw source files are checked against SHA-256 values in the committed catalog before ingestion. Hash mismatch is a data error and generation stops.

## Deterministic versus Model-Controlled Output

The application controls page paths, titles, H1 headings, front matter, source metadata, source links, locators, related-note links, review state, index grouping, and rendered ask citations. Gemma returns only JSON matching a narrow schema.

Ask mode has two local model stages: select relevant IDs from the five retrieved passages, then produce supported claims using only those IDs. The renderer rejects IDs outside the retrieved set. The unsupported evaluation also has a deterministic named-term and lexical-coverage preflight, so a missing requested fact does not need a model guess.

## Modes

| Mode | History | Retrieval | Temperature | Output contract |
| --- | --- | --- | --- | --- |
| Search | none | always | none | verbatim passages |
| Ask | never | always | 0.0 | supported claims or insufficient evidence |
| Chat | latest 8 messages / 6,000 chars | conditional | 0.4 | concise study partner |
| Ingest | none | configured sources | 0.1 | bounded page fields |

All model calls use `num_ctx=8192` and `gemma3:1b-it-q4_K_M` through Ollama's local `/api/chat` endpoint.

## Review and Change Safety

New pages are written as `pending`. `wiki review --show "Title"` supports source comparison, and approval changes the state to `reviewed`. Only reviewed pages appear in the topic-grouped index.

The generation state records the source-hash fingerprint for each page. Unchanged sources skip generation. If a reviewed page's source fingerprint changes, the new output is written under `data/drafts/` for review; the reviewed vault page is never overwritten automatically.

## Failure Semantics

- A normal unsupported research question returns a clear insufficient-evidence answer with exit code 0.
- CLI/configuration errors return 2.
- local-model availability or tag failures return 3.
- extraction, catalog, index, or data failures return 4.

There is no network client other than the configurable Ollama loopback URL. `doctor --offline` reads the local network-interface state, and offline evaluation refuses to start unless Wi-Fi is reported off.
