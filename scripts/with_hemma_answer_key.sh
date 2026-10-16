#!/usr/bin/env bash
# Runs a command with the OpenAI answer-key API key read from Hemma, for live runs such as
#   scripts/with_hemma_answer_key.sh pdm run exam-conversion-eval --grouping-only --evidence-dir <dir>
#   scripts/with_hemma_answer_key.sh env PYTHONPATH=src pdm run python -m scripts.item_type_labeler_live
# The key lives only in this process environment; it is never written or printed.
set -euo pipefail
key_line="$(ssh hemma "grep '^OPENAI_LLM_ANSWER_KEY_API_KEY=' /home/paunchygent/apps/skriptoteket/.env")"
OPENAI_LLM_ANSWER_KEY_API_KEY="${key_line#OPENAI_LLM_ANSWER_KEY_API_KEY=}"
OPENAI_LLM_ANSWER_KEY_API_KEY="${OPENAI_LLM_ANSWER_KEY_API_KEY%\"}"
OPENAI_LLM_ANSWER_KEY_API_KEY="${OPENAI_LLM_ANSWER_KEY_API_KEY#\"}"
export OPENAI_LLM_ANSWER_KEY_API_KEY
unset key_line
exec "$@"
