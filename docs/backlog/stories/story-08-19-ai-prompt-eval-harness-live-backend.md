---
type: story
id: ST-08-19
title: "AI prompt evaluation harness (live backend + llama.cpp)"
status: done
owners: "agents"
created: 2025-12-31
updated: 2026-01-01
epic: "EPIC-08"
dependencies:
  - "ST-08-14"
  - "ST-08-16"
  - "ST-08-18"
links: ["EPIC-08", "SPR-2026-01-05"]
acceptance_criteria:
  - "Given the backend is running locally and a bootstrap account is configured, when the harness runs, then it authenticates via the real HTTP flow (session cookie + CSRF) and can call /api/v1/editor/completions and /api/v1/editor/edits"
  - "Given a fixture bank of realistic editor contexts, when the harness runs, then it executes the full set and produces a deterministic summary report (no prompts/code stored)"
  - "Given responses include empty/truncated/over-budget cases, when the harness classifies outcomes, then it records per-fixture and aggregate counts for ok/empty/truncated/over_budget/timeout/error"
  - "Given prompt template IDs are in use, when the harness runs, then the report records which template ID was used for each request"
  - "Given the harness writes artifacts, when it completes, then it writes only metadata to `.artifacts/ai-prompt-eval/` and never stores user code, prompt text, or model outputs beyond size/flags"
---

## Context

Prompt composition and budgeting must be validated against the **real pipeline** (FastAPI → provider → llama.cpp).
Without a systematic harness we risk:

- ad hoc testing that misses edge cases (large selections, long prefixes, suffix-heavy files)
- regressions when Contract v2 or prompt templates evolve
- silent drift in latency/empty-result rate

We need a repeatable evaluation harness that tests reliability and determinism without storing sensitive content.

## Scope

### 1) Fixture bank (realistic but non-sensitive)

- Create a repo-owned fixture bank of editor contexts, each with:
  - fixture id
  - capability (`inline` or `edit`)
  - language (python)
  - prefix/suffix and (for edits) selection + instruction
  - expected classification constraints (e.g. “must not 500”, “must not be over budget”)
- Include a variety of sizes and shapes:
  - small/medium/large prefix
  - suffix-heavy cases
  - large selection cases
  - contract-focused examples (outputs table/json/html_sandboxed)
  - Swedish user-facing messages

### 2) Live backend runner script

- Add a Python script that:
  - logs in using existing bootstrap credentials from `.env`
  - obtains session cookie + CSRF token
  - calls:
    - `POST /api/v1/editor/completions`
    - `POST /api/v1/editor/edits`
  - measures latency per request
  - classifies results using only metadata

### 3) “Over budget” and “truncated” classification support

To make the harness useful, it must distinguish “model returned empty” vs “backend dropped result due to safety rules”.
Implement one of:

- response headers or a small `meta` object enabled only in eval mode (admin-only and/or dev-only), containing:
  - prompt template id
  - outcome classification (ok/empty/truncated/over_budget/timeout/error)
  - prompt part sizes (chars and/or estimated tokens)

### 4) Artifact output (metadata only)

- Write artifacts to `.artifacts/ai-prompt-eval/<timestamp>/`:
  - `summary.json` (aggregate metrics)
  - `cases.jsonl` (one line per fixture, metadata only)
- Never store:
  - prompt text
  - user code
  - model output text

## Non-goals

- UI automation (Playwright) — keep this harness fast and iteration-friendly
- A/B testing prompt variants (handled separately)
- Provider switching to Tabby (handled separately)

## Notes

- The harness should be designed to run repeatedly and generate comparable reports across runs.
- This story depends on ST-08-18 (prompt template IDs + composition system).
