---
type: pr
id: PR-0046
title: "AI: inline completion harness (gpt-5-nano call logic)"
status: done
owners: "agents"
created: 2026-01-18
updated: 2026-01-21
stories:
  - "ST-08-32"
tags: ["backend", "ai", "testing", "docs"]
acceptance_criteria:
  - "The harness runs GPT-5-nano insertion variants (delimiter + structured output) across script-bank fixtures with token caps 64/128 and streaming enabled."
  - "Harness runs record capture envelopes under ARTIFACTS_ROOT/llm-captures with raw stream events and computed metrics."
  - "Local llama.cpp baselines retain FIM prompts and are reported separately from GPT-5-nano runs."
---

## Problem

Inline completions on GPT-5-nano are verbose and repeat prefix code. We need a production-like harness
that validates call logic (prompt structure + parameters) using real script-bank fixtures and streaming
Responses API events.

## Goal

- Build a repeatable inline completion harness with GPT-5-nano insertion variants.
- Capture raw stream events and compute duplication metrics.
- Preserve local llama.cpp FIM baselines for comparison.

## Non-goals

- Changing production inline completion logic.
- Adding UI flows or new API endpoints.
- Building observability dashboards.

## Implementation plan

1. Add harness module under `scripts/llm_harness/` with CLI entry.
2. Build fixture map from script-bank slugs + scenario anchors.
3. Implement GPT-5-nano request variants (delimiter + structured output).
4. Implement metric computation and capture envelope writing.
5. Document the harness spec in `docs/reference/` and update index.

## Test plan

- Run harness against OpenAI with token caps 64/128.
- Review captures and ensure metrics match thresholds.
- Confirm structured output variant yields insert-only output.

## Rollback plan

- Remove harness module and reference docs; no production behavior changes.
