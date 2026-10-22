# AI Prompt Eval Harnesses

This folder contains **non-sensitive** evaluation harnesses for Skriptoteket AI features.
All harnesses must avoid logging prompt contents to stdout/stderr or artifacts.

Primary reference:

- Editor AI pipeline: `docs/runbooks/run-skript-runbook-editor-ai-pipeline-completion-chat-edit-ops-runbook-editor-ai-pipeline-completion-chat-edit-ops.md`

## Harnesses

### Live backend eval (prompt composition + API)

File: `scripts/ai_prompt_eval/run_live_backend.py`

Purpose:

- Exercises the full backend flow (auth + prompt composition + the HuleEdu LLM provider door call).
- Uses fixtures from `scripts/ai_prompt_eval/fixture_bank.py`: inline-completion fixtures go to
  `POST /api/v1/editor/completions`; edit fixtures go to `POST /api/v1/editor/edit-ops` as the
  route's request model (prefix + selection + suffix as `tool.py`, the selection range, the
  instruction as message, a fixed eval tool id that only a superuser may use).
- Modules: `cli.py` (configuration), `fixture_requests.py` (fixture to request), `fixture_execution.py`
  (one call), `interpretation.py` (eval headers, bodies, outcomes), `reporting.py` (artifacts).
- Talks only to the Skriptoteket HTTP API; it never calls a model endpoint itself.

Artifacts:

- Metadata-only JSON summaries under `.artifacts/ai-prompt-eval/`.

## Adding or modifying harnesses

When a harness is added or changed:

1. Update this README.
2. Update the editor AI pipeline runbook link above if the harness changes how the pipeline is run.
3. Update `docs/index.md` so the documentation index stays complete.
