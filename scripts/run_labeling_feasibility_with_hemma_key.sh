#!/usr/bin/env bash
# Runs the labeling feasibility experiment with the OpenAI key read from Hemma.
# The key lives only in this process environment; it is never written or printed.
set -euo pipefail
key_line="$(ssh hemma "grep '^OPENAI_LLM_ANSWER_KEY_API_KEY=' /home/paunchygent/apps/skriptoteket/.env")"
OPENAI_LLM_ANSWER_KEY_API_KEY="${key_line#OPENAI_LLM_ANSWER_KEY_API_KEY=}"
OPENAI_LLM_ANSWER_KEY_API_KEY="${OPENAI_LLM_ANSWER_KEY_API_KEY%\"}"
OPENAI_LLM_ANSWER_KEY_API_KEY="${OPENAI_LLM_ANSWER_KEY_API_KEY#\"}"
export OPENAI_LLM_ANSWER_KEY_API_KEY
unset key_line
exec env PYTHONPATH=src pdm run python -m scripts.labeling_feasibility "$@"
