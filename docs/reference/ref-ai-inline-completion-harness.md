---
type: reference
id: REF-ai-inline-completion-harness
title: "Reference: Inline completion harness"
status: active
owners: "agents"
created: 2026-01-18
topic: "ai-completions"
---

## Overview

This reference defines the inline completion experiment harness used to validate GPT-5-nano call logic
and compare against local llama.cpp (Devstral) behavior. The harness simulates tab-accept completions
using script-bank fixtures, records raw streamed outputs, and computes duplication/verbosity metrics.

## Scope

- GPT-5-nano Requests API insertion prompts (prefix/suffix with hard delimiters).
- Structured output variant returning `{ "insert": "..." }` for strict insert-only parsing.
- Local llama.cpp baseline runs using FIM prompts (kept separate).
- Metrics + capture envelopes written under `ARTIFACTS_ROOT/llm-captures/`.

## Script Bank Fixtures

Selected slugs:

- `demo-settings-test`
- `demo-inputs`
- `demo-regression-table`
- `ist-vh-mejl-bcc`

## Scenarios

Each slug generates five insert-only scenarios:

- Finish function (complete missing tail)
- Indentation insert (fill missing indented block)
- Spelling correction (single-char insert)
- Inline comment insertion (single line)
- Small refactor insertion (local line add)

## GPT-5-nano Prompt Variants

Variant B (delimiter insertion):

- System instructions: insert-only, no markdown, do not repeat prefix/suffix.
- User content: Language + file path + `<PREFIX>` + `<SUFFIX>` + `<CURSOR>` tags.

Variant C (structured output):

- Same as Variant B, but output is strict JSON: `{ "insert": "..." }`.

## Parameters (Test Matrix)

For each slug × scenario × variant:

- `max_output_tokens`: 64 and 128
- `stream`: true
- `reasoning.effort`: minimal
- `text.verbosity`: low
- `store`: false
- `truncation`: auto

## Capture Envelope

Captures follow the existing envelope format:

- Location: `ARTIFACTS_ROOT/llm-captures/inline_completion_harness/<capture_id>/capture.json`
- Payload includes:
  - slug, scenario, variant, params
  - request + raw stream events
  - final completion
  - metrics

## Metrics

Primary metrics:

- Duplication ratio (< 5%)
- Prefix echo detection (no re-declaring imports/defs in dict literals)
- Line count (<= 12 lines unless finish-function scenario)

Secondary metrics:

- Indentation match
- Context alignment at cursor

## Local llama.cpp Baselines

- Keep FIM prompt logic for Devstral.
- Report results separately from GPT-5-nano.
