#!/bin/sh
set -eu

WIKI=".venv/bin/wiki"

printf '\n$ wiki --help\n'
"$WIKI" --help

printf '\n$ wiki doctor  # local checks; Wi-Fi state recorded honestly\n'
"$WIKI" doctor

printf '\n$ wiki ingest ./vault/raw\n'
"$WIKI" ingest ./vault/raw

printf '\n$ wiki ask "Which dimensions do the course materials use to compare health systems?" --mode local\n'
"$WIKI" ask "Which dimensions do the course materials use to compare health systems?" --mode local

printf '\n$ wiki ask "Why can an approved healthcare product still fail to reach a patient?" --mode local\n'
"$WIKI" ask "Why can an approved healthcare product still fail to reach a patient?" --mode local

printf '\n$ wiki ask "How does moving from fee-for-service toward value-based payment change provider accountability?" --mode local\n'
"$WIKI" ask "How does moving from fee-for-service toward value-based payment change provider accountability?" --mode local

printf '\n$ wiki ask "What percentage of Chilean patients received same-day primary care in 2026?" --mode local\n'
"$WIKI" ask "What percentage of Chilean patients received same-day primary care in 2026?" --mode local

printf '\n$ wiki search "payment methods from fee for service to two-sided risk" --limit 5\n'
"$WIKI" search "payment methods from fee for service to two-sided risk" --limit 5

printf '\n$ wiki chat  # capability, plan, and follow-up continuity\n'
printf 'what can you help me with?\nGive me a generic three-step study plan.\nmake that shorter\n/quit\n' | "$WIKI" chat

printf '\n$ wiki eval run  # local Ollama; no hosted API\n'
"$WIKI" eval run
