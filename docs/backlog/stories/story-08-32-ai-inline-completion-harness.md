---
type: story
id: ST-08-32
title: "AI: inline completion harness (gpt-5-nano logic validation)"
status: ready
owners: "agents"
created: 2026-01-18
epic: "EPIC-08"
acceptance_criteria:
  - "Given the harness, when run against script-bank fixtures, then it exercises the GPT-5-nano insertion variants (delimiter and structured output) across the defined scenarios and token caps (64/128)."
  - "Given each run, when results are captured, then the harness writes a capture envelope under ARTIFACTS_ROOT/llm-captures with raw stream events, params, and computed metrics (duplication ratio, line count, indentation match)."
  - "Given local llama.cpp baselines, when the harness is configured for local runs, then it preserves FIM-based prompts and reports results separately from GPT-5-nano."
---

## Context

We need a repeatable, production-like harness to validate inline completion call logic for GPT-5-nano and
compare against local llama.cpp (FIM) behavior. The harness uses script-bank fixtures, runs realistic
insert-only scenarios, and records outputs in the standard capture envelope for later analysis.

## Notes

- Reference spec: `docs/reference/ref-ai-inline-completion-harness.md`
- PR plan: `docs/backlog/prs/pr-0046-ai-inline-completion-harness.md`
