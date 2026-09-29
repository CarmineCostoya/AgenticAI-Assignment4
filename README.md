# AgenticAI-Assignment4: Offline Healthcare Wiki

A submission-ready personal wiki and retrieval-augmented CLI for the Fall 2026 *Healthcare in the 21st Century* course. The project runs locally on an 8 GB Apple M1 MacBook Air with Ollama's exact `gemma3:1b-it-q4_K_M` model. It does not use a hosted API, remote fallback, persistent personal memory, or online retrieval.

The repository is intentionally auditable: original course files are preserved byte-for-byte, retrieval returns original passages, citations are rendered by the application rather than the model, and measured evidence is committed separately from rebuildable runtime state.

## Quick Start

Requirements: macOS, Python 3.9 or newer, and [Ollama](https://ollama.com/download). Obsidian is optional and is used only to view the `vault/` directory.

After cloning the repository:

```bash
cd AgenticAI-Assignment4

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .

ollama pull gemma3:1b-it-q4_K_M
.venv/bin/wiki ingest ./vault/raw
.venv/bin/wiki --help
```

The exact model tag is required. The [official Ollama model entry](https://ollama.com/library/gemma3:1b-it-q4_K_M) describes an approximately 815 MB, 32K-context quantized Gemma 3 model. This application deliberately limits requests to `num_ctx=8192` to leave memory headroom on the 8 GB machine.

## Commands

```text
wiki ingest ./vault/raw
wiki search "payment methods from fee for service to two-sided risk" --limit 5
wiki ask "Why can an approved healthcare product still fail to reach a patient?" --mode local
wiki chat
wiki review
wiki doctor --offline
wiki eval run --offline
```

- `ingest` validates catalog hashes, extracts and indexes originals, generates pending-review notes, and refreshes the index page. Unchanged reviewed notes are skipped; a changed source stages drafts under ignored `data/drafts/` instead of overwriting reviewed work.
- `search` prints verbatim passages, source paths, locators, and BM25-derived scores. It never calls Gemma.
- `ask` is a standalone, history-free research mode. It retrieves five passages, asks Gemma for schema-constrained claims, rejects unknown evidence IDs, and renders citations deterministically.
- `chat` is a concise study partner with at most eight recent messages and a 6,000-character history budget. Greetings, capability questions, generic planning, and drafting revisions bypass retrieval.
- `review` shows or approves generated pages after human source comparison.
- `doctor --offline` verifies source hashes, SQLite FTS5, the exact model tag, Ollama, hardware, wiki links, and Wi-Fi state without contacting the internet.
- `eval run --offline` refuses to run until Wi-Fi is confirmed off, then records the fixed ask, chat, and search checks.

Normal insufficient-evidence answers exit successfully. Input/configuration errors use exit code 2, model availability errors use 3, and data/extraction/index errors use 4.

## Repository Map

| Path | Purpose |
| --- | --- |
| [`src/personal_wiki/`](src/personal_wiki/) | CLI, extraction, retrieval, Ollama client, grounding, review, doctor, and evaluation code |
| [`config/wiki_pages.json`](config/wiki_pages.json) | Stable titles, folders, source focus, and related-note links |
| [`data/source_catalog.json`](data/source_catalog.json) | Source IDs, authorship, provenance, permission, and SHA-256 hashes |
| [`vault/raw/`](vault/raw/) | Three unchanged source files |
| [`vault/wiki/`](vault/wiki/) | Five reviewed wiki pages |
| [`vault/index.md`](vault/index.md) | Topic-grouped entry point populated from reviewed pages |
| [`evals/questions.json`](evals/questions.json) | Fixed ask and mode-boundary evaluation cases |
| [`evidence/`](evidence/) | Actual model outputs, passages, timing, memory, offline proof, and screenshots |
| [`tests/`](tests/) | Standard-library automated test suite |

The full data flow and trust boundaries are in [Architecture](docs/architecture.md). The complete source manifest is [data/source_catalog.json](data/source_catalog.json).

## Reviewed Wiki

- [Healthcare System Structure](vault/wiki/Systems/Healthcare%20System%20Structure.md)
- [Healthcare Costs and Value](vault/wiki/Concepts/Healthcare%20Costs%20and%20Value.md)
- [Reimbursement and Access](vault/wiki/Concepts/Reimbursement%20and%20Access.md)
- [Fee for Service](vault/wiki/Concepts/Fee%20for%20Service.md)
- [Value Based Payment](vault/wiki/Concepts/Value%20Based%20Payment.md)

All five pages are marked `review_status: reviewed`. Filenames, H1 headings, front matter, locators, source links, and internal links are application-controlled. Gemma supplies only bounded summary/detail fields; each note was then compared with its sources and corrected before approval.

## Retrieval and Grounding

- PDFs become one original passage per slide. DOCX content is grouped by heading; long sections use 350-word chunks with 60-word overlap.
- SQLite FTS5 stores original passage text. Query-time healthcare synonym expansion improves paraphrase recall without altering stored text.
- Search returns the top five results by default. Ask mode uses deterministic topic expansion and source diversification before model generation.
- Ask first selects directly relevant evidence IDs, then generates one to three claims at temperature 0. Every evidence ID must exist in the retrieved packet. Missing facts, unknown citations, or invalid structured output fail closed to an explicit insufficient-evidence response.
- Chat uses temperature 0.4, ingestion uses 0.1, and all calls use `num_ctx=8192`.

## Tests

```bash
PYTHONPYCACHEPREFIX=/tmp/wiki-pycache \
  .venv/bin/python -m unittest discover -s tests -v
```

The suite covers committed hashes, PDF/DOCX locators, 350/60 chunk boundaries, FTS ranking and synonym expansion, search without a model, citation rejection, ask/chat isolation, routing and follow-up continuity, title/heading rules, internal links, and idempotent re-ingestion. Current result: **16 tests passed**.

## Actual Local Measurements

The successful ingestion indexed **73 passages**: 40 from the study guide, 16 slides from the Aug. 31 deck, and 17 slides from the Sep. 21 deck. Four page generations in the resumed run took **56.859 seconds** total; individual generations took **12.765–14.544 seconds**. Sampled Ollama resident memory was **935.12–977.45 MB**, and the loaded model allocation reported **838.51 MB**. See [generation.json](evidence/ingest/generation.json).

Duplicate-free re-ingestion skipped all five reviewed pages, produced no drafts, and completed in **0.847 seconds**. See [reingest.json](evidence/ingest/reingest.json).

These are measurements from this machine, not estimates. Per-answer latency, token counts, and sampled memory are recorded in each final [ask evidence card](evidence/ask/).

## Submission Evidence

- [Evidence index](evidence/README.md)
- [Ask 1: health-system comparison dimensions](evidence/ask/ask-01.md)
- [Ask 2: approval versus patient access](evidence/ask/ask-02.md)
- [Ask 3: fee-for-service versus value-based accountability](evidence/ask/ask-03.md)
- [Ask 4: explicit insufficient evidence](evidence/ask/ask-04.md)
- [Chat, follow-up, raw-search, and history-isolation checks](evidence/mode-checks.md)
- [Local doctor and network-state snapshot](evidence/offline/doctor.json)
- [Terminal transcript](evidence/offline/terminal.typescript)
- [Obsidian screenshot index](evidence/README.md#obsidian-screenshots)

## Limitations and Improvement

The 1B model is a deliberate fit for an 8 GB laptop, but its summaries can omit nuance or produce structurally valid yet weak prose. The project mitigates that risk with bounded schemas, deterministic citations, source review, and fail-closed validation; it does not claim that validation proves semantic entailment automatically. The corpus is fixed, small, and text-extractable, and the system does not implement OCR or current-web fact checking.

A practical next improvement is a local entailment verifier that compares each generated claim with its cited passage before rendering it. That would supplement evidence-ID validation without weakening the offline-only design.

## Reproducible Offline Demonstration

1. Install Ollama and pull the model while online.
2. Run ingestion and review the five pages.
3. Turn Wi-Fi off.
4. Restart the CLI process and run `wiki doctor --offline`.
5. Run `wiki eval run --offline` and capture the terminal session.
6. Turn Wi-Fi back on only after the evidence files are saved.

No model weights, virtual environment, caches, credentials, or rebuildable SQLite database are committed. The completed submission is published at [CarmineCostoya/AgenticAI-Assignment4](https://github.com/CarmineCostoya/AgenticAI-Assignment4), and public access was confirmed with an unauthenticated HTTP request.

The committed final evaluation was run locally with Wi-Fi on, as explicitly permitted during the final capture, and is honestly marked `offline: false`; Ollama was still the only model endpoint. The `--offline` gate is implemented and refuses to run unless macOS confirms Wi-Fi is off. A grader can reproduce the stricter offline procedure above after the model has been pulled.
