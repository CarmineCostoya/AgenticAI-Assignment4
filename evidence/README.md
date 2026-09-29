# Evidence Index

This directory stores actual, unedited model outputs from the final local run plus human assessments added afterward. Evidence files are created by `wiki eval run` (or `wiki eval run --offline` when Wi-Fi is disabled); screenshots are added after the final Obsidian and terminal demonstrations.

## Required evidence

- `ask/ask-01.md` through `ask/ask-04.md`: fixed ask-mode evidence cards.
- `mode-checks.md`: chat, follow-up, raw-search, and chat-history-separation checks.
- `offline/doctor.json`: local model, source hashes, device, and network-interface snapshot. The final capture honestly records `offline_requested: false` and Wi-Fi on, per the user's final instruction.
- `offline/terminal.typescript`: terminal recording captured with macOS `script`.
- `obsidian/01-note.png`: open reviewed note with sources and related links.
- `obsidian/02-index.png`: topic-organized index and page list.
- `obsidian/03-graph.png`: graph filtered to `path:"wiki"` with attachments hidden.
- `source-render-qa.md`: every page/slide render inspection and locator check.
- `wiki-review.md`: human review and approval record for all five generated notes.

The terminal capture was produced by [`scripts/offline_demo.sh`](../scripts/offline_demo.sh). For the committed run it invokes the local-mode commands without `--offline`, matching the user's final permission; switching those two calls back to `--offline` restores the stricter Wi-Fi gate.

## Obsidian Screenshots

- [Capture status and exact remaining steps](obsidian/README.md)
- [Reviewed Reimbursement and Access note](obsidian/01-note.png)
- [Grouped index and wiki file list](obsidian/02-index.png)
- [Wiki-only graph with attachments hidden](obsidian/03-graph.png)

Missing files represent evidence that has not yet been honestly captured; they are never replaced with invented output.
