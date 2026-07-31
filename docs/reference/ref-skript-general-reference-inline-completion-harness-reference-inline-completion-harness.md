---
type: reference
id: REF-SKRIPT-GENERAL-reference-inline-completion-harness
title: 'Reference: Inline completion harness'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: general
retired_ids:
- REF-ai-inline-completion-harness
summary: 'Reference: Inline completion harness'
---

## Overview


This reference defines the inline completion experiment harness used to validate GPT-5-nano call logic
and compare against local llama.cpp (Devstral) behavior. The harness simulates tab-accept completions
using script-bank fixtures, records raw streamed outputs, and computes duplication/verbosity metrics.

## Facts And Semantics

No separate facts and semantics is stated in the source.

### Source: Scope


- GPT-5-nano Requests API insertion prompts (prefix/suffix with hard delimiters).
- Structured output variant returning `{ "insert": "..." }` for strict insert-only parsing.
- Local llama.cpp baseline runs using FIM prompts (kept separate).
- Metrics + capture envelopes written under `ARTIFACTS_ROOT/llm-captures/`.

### Source: Script Bank Fixtures


Selected slugs:

- `demo-settings-test`
- `demo-inputs`
- `demo-regression-table`
- `ist-vh-mejl-bcc`

### Source: Scenarios


Each slug generates five insert-only scenarios:

- Finish function (complete missing tail)
- Indentation insert (fill missing indented block)
- Spelling correction (single-char insert)
- Inline comment insertion (single line)
- Small refactor insertion (local line add)

### Source: GPT-5-nano Prompt Variants


Variant B (delimiter insertion):

- System instructions: insert-only, no markdown, do not repeat prefix/suffix.
- User content: Language + file path + `<PREFIX>` + `<SUFFIX>` + `<CURSOR>` tags.

Variant C (structured output):

- Same as Variant B, but output is strict JSON: `{ "insert": "..." }`.

### Source: Parameters (Test Matrix)


For each slug × scenario × variant:

- `max_output_tokens`: 64 and 128
- `stream`: true
- `reasoning.effort`: minimal
- `text.verbosity`: low
- `store`: false
- `truncation`: auto

### Source: Capture Envelope


Captures follow the existing envelope format:

- Location: `ARTIFACTS_ROOT/llm-captures/inline_completion_harness/<capture_id>/capture.json`
- Payload includes:
  - slug, scenario, variant, params
  - request + raw stream events
  - final completion
  - metrics

### Source: Metrics


Primary metrics:

- Duplication ratio (< 5%)
- Prefix echo detection (no re-declaring imports/defs in dict literals)
- Line count (<= 12 lines unless finish-function scenario)

Secondary metrics:

- Indentation match
- Context alignment at cursor

### Source: Local llama.cpp Baselines


- Keep FIM prompt logic for Devstral.
- Report results separately from GPT-5-nano.

## Decisions And Interpretation

No separate decisions and interpretation is stated in the source.
