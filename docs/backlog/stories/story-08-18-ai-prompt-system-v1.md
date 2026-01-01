---
type: story
id: ST-08-18
title: "AI prompt system v1 (templates + contract fragments + validation)"
status: done
owners: "agents"
created: 2025-12-31
updated: 2026-01-01
epic: "EPIC-08"
dependencies:
  - "ADR-0043"
  - "ADR-0044"
links: ["EPIC-08", "SPR-2026-01-05", "ADR-0043", "ADR-0044"]
acceptance_criteria:
  - "Given a prompt template uses placeholders for code-owned fragments, when the backend composes a system prompt, then all placeholders are resolved and no unknown placeholders remain"
  - "Given Contract v2 changes, when the canonical contract fragment is updated, then all capabilities that reference the fragment automatically pick up the change (no duplicated contract text per template)"
  - "Given each capability requires specific fragments (e.g., contract + runner constraints), when a template omits a required fragment placeholder, then tests fail"
  - "Given a composed prompt and a configured system-prompt budget, when the prompt is validated, then it stays within the configured budget (token-estimation or deterministic budget rules) or the build/test fails"
  - "Given prompt template IDs are configured, when a completion/edit request runs, then the backend logs the template ID (metadata only; no prompt/code)"
---

## Context

Skriptoteket’s AI editor capabilities (inline completions + edit suggestions) depend on system prompts being:

- **Deterministic** (same inputs → same prompt structure)
- **Up-to-date with Contract v2** (outputs schema, limits, conventions)
- **Stable over time** (reviewable diffs, versioned templates)
- **Budget-aware** (llama.cpp `n_ctx` hard limits: prompt + output)

Today we have ad hoc prompt text in templates. This story formalizes prompt composition as a first-class subsystem with:

- human-editable **templates** per capability (inline vs edit)
- code-owned **fragments** for contract-sensitive content
- automated **validation** so drift is caught early

## Delivered (implementation)

- **Template registry + IDs:** `src/skriptoteket/application/editor/prompt_templates.py`
  - IDs selected via env vars: `LLM_COMPLETION_TEMPLATE_ID`, `LLM_EDIT_TEMPLATE_ID` (`src/skriptoteket/config.py`)
- **Code-owned fragments (single source of truth):** `src/skriptoteket/application/editor/prompt_fragments.py`
  - Contract v2 + policy budgets/caps sourced from `src/skriptoteket/domain/scripting/ui/contract_v2.py` and
    `src/skriptoteket/domain/scripting/ui/policy.py`
  - Runner constraints sourced from `src/skriptoteket/config.py` (timeouts/limits)
- **Composition + validation:** `src/skriptoteket/application/editor/prompt_composer.py`
  - Placeholder format: `{{FRAGMENT_NAME}}` (strict regex + allowlist)
  - Validates required placeholders, unknown placeholders, unresolved placeholders, and system-prompt budget using the
    existing deterministic char→token approximation (`src/skriptoteket/application/editor/prompt_budget.py`)
  - Unit tests: `tests/unit/application/test_ai_prompt_system_v1.py`
- **Templates migrated to placeholders:** `src/skriptoteket/application/editor/system_prompts/*.txt`
- **Observability (metadata only):** template IDs logged per request in:
  - `src/skriptoteket/application/editor/completion_handler.py`
  - `src/skriptoteket/application/editor/edit_suggestion_handler.py`

## Scope

### 1) Prompt template registry

- Introduce a registry of prompt templates with stable IDs, e.g.:
  - `inline_completion_v1`
  - `edit_suggestion_v1`
- Each template has:
  - ID
  - file path
  - capability (inline/edit)
  - required fragment placeholders

### 2) Code-owned fragments (Contract v2 + runner constraints)

- Create a small fragment module layer that produces strings for inclusion in templates, e.g.:
  - `CONTRACT_V2_FRAGMENT`
  - `RUNNER_CONSTRAINTS_FRAGMENT`
  - `HELPERS_FRAGMENT`
- Contract-sensitive fragments MUST be sourced from (or generated from) the canonical backend definitions used to
  validate/describe the contract (single source of truth).

### 3) Template composition + validation

- Templates remain human-editable text files and include placeholders such as `{{CONTRACT_V2_FRAGMENT}}`.
- Composition loads the template, replaces placeholders with fragment text, and validates:
  - no unknown placeholders
  - no unresolved placeholders
  - required placeholders present
  - resulting prompt passes budget validation (for the configured system prompt budget)

### 4) Observability hooks (metadata only)

- Log the prompt template ID used for each request (inline/edit) without logging prompt/code.
- (If needed) add a test-only / eval-only mode to surface the template ID to the evaluation harness.

## Non-goals

- Prompt A/B testing (handled in ST-08-17 and future stories)
- Retrieval augmentation / repo indexing (Tabby, embeddings)
- Changing LLM provider routing
- Changing UI behavior

## Notes

- Existing prompt templates should be migrated to placeholders so Contract v2 content is not duplicated across files.
- This story should align with:
  - `docs/reference/ref-ai-completion-architecture.md`
  - `docs/reference/reports/ref-ai-edit-suggestions-kb-context-budget-blocker.md`
  - ADRs: `ADR-0043`, `ADR-0050`
