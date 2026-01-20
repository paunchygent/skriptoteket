---
type: story
id: ST-08-33
title: "AI: inline completion normalization + token budgets"
status: ready
owners: "agents"
created: 2026-01-19
epic: "EPIC-08"
acceptance_criteria:
  - "Given local FIM inline completions are enabled, when a completion request is sent, then the local provider uses `max_tokens=64` and preserves the existing FIM prompt format."
  - "Given OpenAI GPT-5-nano inline completions are enabled, when a completion request is sent, then the provider uses the delimiter prompt format via Responses API with `max_output_tokens=64` (no structured-output parsing path)."
  - "Given a completion response includes duplicated content from the prefix/suffix, when normalization runs, then any 2-line contiguous block echo drops the completion; otherwise exact duplicate lines (>=12 non-whitespace chars) are stripped and empty results return an empty completion."
  - "Given a completion repeats the prefix tail at the cursor boundary (e.g. `def run_tooldef run_tool(...)`), when normalization runs, then the returned completion removes the overlap so the insertion starts after the cursor."
  - "Given a completion response is fenced or quoted, normalization strips the wrappers; if upstream returns a partial completion with `finish_reason=length` or `finish_reason=incomplete`, the system still normalizes and returns a best-effort completion."
---

## Context

Inline completions must be short, fast, and insert-ready. Harness + live usage show that:

- Both local and remote models can echo existing context.
- OpenAI Responses may return useful partial output alongside `finish_reason=length|incomplete`.

We need a deterministic normalization pass and a sensible shared token budget (`max_output_tokens=64`) while
keeping the local FIM prompt format stable.

## Notes

- Reference harness: `docs/reference/ref-ai-inline-completion-harness.md`
- PR plan: `docs/backlog/prs/pr-0047-ai-inline-completion-normalization-and-caps.md`
