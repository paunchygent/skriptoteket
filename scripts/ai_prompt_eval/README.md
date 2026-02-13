# AI Prompt Eval Harnesses

This folder contains **non-sensitive** evaluation harnesses for Skriptoteket AI features.
All harnesses must avoid logging prompt contents to stdout/stderr or artifacts.

Primary references:
- Runbook: `docs/runbooks/runbook-gpu-ai-workloads.md`
- Editor AI pipeline: `docs/runbooks/runbook-editor-ai-pipeline.md`

## Harnesses

### 1) Live backend eval (prompt composition + API)

File: `scripts/ai_prompt_eval/run_live_backend.py`

Purpose:
- Exercises the full backend flow (auth + prompt composition + LLM call).
- Uses fixtures from `scripts/ai_prompt_eval/fixture_bank.py`.

Artifacts:
- Metadata-only JSON summaries under `.artifacts/ai-prompt-eval/`.

### 2) Canonical chat burn (llama.cpp stability)

File: `scripts/ai_prompt_eval/llama_canonical_chat_burn.py`

Purpose:
- Stress test llama.cpp chat completions (review + diff) for stability.
- Uses canonical fixtures from:
  `docs/reference/reports/artifacts/llama-canonical-chat-v3/llama-canonical-chat-v3-20260105T012947Z/`

Artifacts:
- Log file in the chosen log directory (no prompt contents).

### 3) Kodassistenten eval (llama.cpp behavior + compliance)

File: `scripts/ai_prompt_eval/llama_kodassistent_eval.py`

Purpose:
- Evaluate **model behavior** on Kodassistenten-specific constraints:
  runner limits, UI payload contract, toolkit usage, action/state flow.
- Runs directly against llama.cpp to keep prompts stable across models.

Fixture directory:
- `docs/reference/reports/artifacts/llama-kodassistent-eval-v2/llama-kodassistent-eval-v2-20260131T150000Z/`

Outputs (per run directory):
- `<label>_review.response.json`
- `<label>_review.text`
- `<label>_diff_tool.response.json`
- `<label>_diff_tool.text`
- `<label>_diff_schema.response.json`
- `<label>_diff_schema.text`
- `comparison.json` (usage/timing per label)
- `validation.json` (pass/fail + reasons per label)

Run example:
```bash
python3 scripts/ai_prompt_eval/llama_kodassistent_eval.py --label glm
python3 scripts/ai_prompt_eval/llama_kodassistent_eval.py --label devstral --output-dir .artifacts/llama-kodassistent-eval-v2/<same-run-dir>
```

Skip schema diff step (tool.py only):
```bash
python3 scripts/ai_prompt_eval/llama_kodassistent_eval.py --label glm --skip-schema-diff
```

System prompt options:
```bash
# Default: build system prompt from editor_chat_v1
python3 scripts/ai_prompt_eval/llama_kodassistent_eval.py --label glm

# Disable system prompt injection
python3 scripts/ai_prompt_eval/llama_kodassistent_eval.py --label glm --no-system

# Override with a system prompt file
python3 scripts/ai_prompt_eval/llama_kodassistent_eval.py --label glm --system-prompt-path /path/to/prompt.txt
```

Note: system prompt composition relies on app dependencies (pydantic/settings). If you see import errors,
run via `pdm run python ...` instead of `python3 ...`.

### 4) Single request helper

File: `scripts/ai_prompt_eval/llama_single_request.py`

Purpose:
- Simple utility to send one prompt to llama.cpp (debugging helper).

Supports `--system-prompt-path` to prepend a system message.

## Adding or modifying harnesses

When a harness is added or changed:
1) Update this README.
2) Add or update a **runbook link** in `docs/runbooks/runbook-gpu-ai-workloads.md`.
3) Update `docs/index.md` so the documentation index stays complete.
