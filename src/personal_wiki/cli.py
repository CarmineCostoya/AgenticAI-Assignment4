from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from .config import AppPaths, load_synonyms, model_name, ollama_url
from .doctor import doctor_snapshot
from .evidence import EvalRunner
from .extractors import ExtractionError
from .harness import AskService, ChatService
from .ingest import IngestService
from .ollama import ModelOutputError, ModelUnavailableError, OllamaClient
from .retrieval import PassageIndex
from .wiki_pages import review_pages


EXIT_INPUT = 2
EXIT_MODEL = 3
EXIT_DATA = 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wiki",
        description="Offline healthcare personal wiki using local Gemma, SQLite FTS5, and verifiable citations.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    subparsers = parser.add_subparsers(dest="command")

    ingest = subparsers.add_parser("ingest", help="Validate raw sources, rebuild retrieval, and generate wiki pages")
    ingest.add_argument("source", nargs="?", default="./vault/raw", help="Curated raw-source directory")

    search = subparsers.add_parser("search", help="Show matching original passages without calling Gemma")
    search.add_argument("query", help="Search query")
    search.add_argument("--limit", type=int, default=5, help="Maximum passages (default: 5)")
    search.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    ask = subparsers.add_parser("ask", help="Answer a standalone factual question from retrieved evidence")
    ask.add_argument("question", help="Research question")
    ask.add_argument("--mode", choices=["local"], default="local", help="Execution setting; only local is supported")

    subparsers.add_parser("chat", help="Start the practical study-partner chat")

    review = subparsers.add_parser("review", help="Inspect and approve generated wiki pages")
    review.add_argument("--show", default="", metavar="TITLE", help="Print one generated page for source review")
    review.add_argument("--approve", default="", metavar="TITLE", help="Mark one reviewed page approved")
    review.add_argument("--approve-all", action="store_true", help="Approve all pending pages after manual review")

    doctor = subparsers.add_parser("doctor", help="Check sources, index, local model, device, and wiki integrity")
    doctor.add_argument("--offline", action="store_true", help="Require Wi-Fi to be confirmed off")

    eval_parser = subparsers.add_parser("eval", help="Run and save the fixed assignment evaluation")
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command")
    eval_run = eval_subparsers.add_parser("run", help="Run four ask tests plus chat/search checks")
    eval_run.add_argument("--offline", action="store_true", help="Refuse unless Wi-Fi is confirmed off")
    return parser


def _services(paths: AppPaths):
    index = PassageIndex(paths.database, load_synonyms(paths))
    client = OllamaClient(ollama_url(), model_name())
    return index, client


def _print_search(hits) -> None:
    if not hits:
        print("No matching passages.")
        return
    for hit in hits:
        print(f"{hit.evidence_id} | {hit.source_path} | {hit.locator} | score={hit.score:.6f}")
        print(hit.text)
        print()


def _run_chat(paths: AppPaths, index: PassageIndex, client: OllamaClient) -> int:
    if index.count() == 0:
        raise FileNotFoundError("Retrieval index is missing; run `wiki ingest ./vault/raw` first")
    service = ChatService(paths, index, client)
    history: List[Dict[str, str]] = []
    print(f"Mode: chat | Execution: local | Model: {client.model}")
    print("Commands: /clear, /quit")
    while True:
        try:
            message = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not message:
            continue
        if message.lower() in {"/quit", "/exit"}:
            return 0
        if message.lower() == "/clear":
            history.clear()
            print("Conversation cleared.")
            continue
        result = service.chat(message, history)
        print(f"assistant> {result.text}")
        print(f"[retrieval={'yes' if result.route.retrieve else 'no'}; {result.route.reason}]")
        history.extend([{"role": "user", "content": message}, {"role": "assistant", "content": result.text}])


def dispatch(args: argparse.Namespace, paths: AppPaths) -> int:
    index, client = _services(paths)
    if args.command == "ingest":
        result = IngestService(paths, index, client).run(Path(args.source))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "search":
        hits = index.search(args.query, limit=max(1, min(args.limit, 20)))
        if args.json:
            print(json.dumps([hit.__dict__ for hit in hits], indent=2))
        else:
            print("Mode: search | Execution: local | Model call: none")
            _print_search(hits)
        return 0
    if args.command == "ask":
        if index.count() == 0:
            raise FileNotFoundError("Retrieval index is missing; run `wiki ingest ./vault/raw` first")
        result = AskService(paths, index, client).ask(args.question)
        print(f"Mode: ask | Execution: local | Model: {client.model}")
        print(result.rendered_answer)
        return 0
    if args.command == "chat":
        return _run_chat(paths, index, client)
    if args.command == "review":
        result = review_pages(
            paths,
            approve_title=args.approve,
            approve_all=args.approve_all,
            show_title=args.show,
        )
        if "show" in result:
            print(result["show"])
        else:
            print(json.dumps(result, indent=2))
        return 0
    if args.command == "doctor":
        snapshot = doctor_snapshot(paths, index, client, offline_requested=args.offline)
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0 if snapshot["required_checks_pass"] else EXIT_DATA
    if args.command == "eval" and args.eval_command == "run":
        if index.count() == 0:
            raise FileNotFoundError("Retrieval index is missing; run `wiki ingest ./vault/raw` first")
        ask = AskService(paths, index, client)
        chat = ChatService(paths, index, client)
        result = EvalRunner(paths, index, client, ask, chat).run(offline=args.offline)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    raise ValueError("Choose a command; run `wiki --help` for usage")


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = AppPaths.discover()
    try:
        code = dispatch(args, paths)
    except ModelUnavailableError as exc:
        print(f"Model error: {exc}", file=sys.stderr)
        code = EXIT_MODEL
    except (ExtractionError, ModelOutputError, FileNotFoundError) as exc:
        print(f"Data error: {exc}", file=sys.stderr)
        code = EXIT_DATA
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Input/configuration error: {exc}", file=sys.stderr)
        code = EXIT_INPUT
    raise SystemExit(code)
