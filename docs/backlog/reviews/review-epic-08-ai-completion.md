---
type: review
id: REV-EPIC-08
title: "Review: AI Completion Integration for EPIC-08"
status: approved
owners: "agents"
created: 2025-12-26
reviewer: "lead-developer"
epic: EPIC-08
adrs:
  - ADR-0043
stories:
  - ST-08-14
---

## TL;DR

This review covers the addition of AI-powered inline completions (ST-08-14) to the existing script editor intelligence
system (EPIC-08). The feature adds Copilot-style ghost text using an OpenAI-compatible backend proxy with KB injection.

## Problem Statement

Script authors using the editor benefit from static intelligence (ST-08-10/11/12) but lack dynamic code suggestions.
Writing correct Contract v2 payloads and using available helpers requires KB knowledge that could be surfaced through
AI-powered completions.

## Proposed Solution

- **Backend proxy**: OpenAI-compatible endpoint (`POST /api/v1/editor/completions`) handles LLM calls
- **KB injection**: System prompt includes `ref-ai-script-generation-kb.md` content
- **CodeMirror extension**: Ghost text appears as semi-transparent text at cursor
- **Triggers**: Debounced auto-trigger (1500ms) + manual trigger (Alt+\)
- **Provider-agnostic**: Works with Ollama (local), OpenRouter, OpenAI

See [ADR-0043](../../adr/adr-0043-ai-completion-integration.md) for architecture.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0043-ai-completion-integration.md` | Architecture decision, provider choice | 5 min |
| `docs/reference/ref-ai-completion-architecture.md` | API contract, extension design | 5 min |
| `docs/backlog/stories/story-08-14-ai-inline-completions.md` | Acceptance criteria, scope | 3 min |
| `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md` | Updated scope, story list | 2 min |

**Total estimated time:** ~15 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| OpenAI-compatible API | Supports Ollama (free/local), OpenRouter, OpenAI without vendor lock-in | ✅ |
| Backend proxy (no frontend API keys) | Security: API keys never exposed to browser | ✅ |
| KB injection in system prompt | Ensures suggestions follow runner constraints, Contract v2 | ⚠️ (approved w/ concerns) |
| Fill-in-the-middle format | Standard approach for code completion prompts | ⚠️ (approved w/ concerns) |
| Debounced auto-trigger (1500ms) | Balances responsiveness vs API load | ⚠️ (approved w/ concerns) |

## Review Checklist

- [ ] ADR defines clear protocol contract (`LLMProviderProtocol`)
- [ ] API endpoint follows existing `editor.py` patterns
- [ ] Story has testable acceptance criteria (Given/When/Then)
- [ ] Security: API keys on backend only, CSRF required
- [ ] Graceful degradation when LLM disabled (`enabled: false`)
- [ ] Integration with existing intelligence bundle is clean

---

## Review Feedback

**Reviewer:** @user-lead
**Date:** 2025-12-26
**Verdict:** changes_requested

### Required Changes

1. Add multi-line completions as explicitly in-scope: update ST-08-14 acceptance criteria + remove "Multi-line ghost text formatting" from Out of Scope; add tests for multi-line render + Tab insertion + truncated suppression.
2. Add `OPENAI_LLM_COMPLETION_API_KEY` to ADR-0043 and ST-08-14 configuration blocks (optional for Ollama).
3. Align rate-limiting claims: ADR-0043 must not assert per-user rate limiting as implemented if it remains out-of-scope in ST-08-14.
4. Update stop-token guidance in ADR-0043 + `ref-ai-completion-architecture`: remove `\n\n`, `def `, `class ` stop tokens; support multi-line blocks.
5. Update `ref-ai-completion-architecture` API contract: completion may include newlines; backend must discard truncated upstream outputs (`finish_reason="length"`) and return empty completion instead of partial blocks.
6. Update KB injection spec: package KB for production, cache it in memory, and define deterministic fallback behavior if KB cannot load.
7. Specify Tab/Escape keymap precedence requirements so Tab acceptance overrides `indentWithTab` when ghost text is visible.
8. Add explicit privacy/logging rules: never log code/prompt contents; clarify third-party code transmission risks.

### Suggestions (Optional)

- Consider a sentinel stop sequence (e.g. `<END_COMPLETION>`) for more reliable multi-line block termination; still discard truncated responses.
- Revisit default `LLM_COMPLETION_MAX_TOKENS` now that multi-line is in scope (256 may truncate frequently); document cost/latency trade-offs.
- Add trigger heuristics (avoid strings/comments; optional end-of-line gating) to reduce noise and request volume.
- Document recommended debounce ranges and encourage measurement (1500ms may feel slow with 1–3s model latency).

### Decision Approvals

- ✅ OpenAI-compatible API
- ✅ Backend proxy (no frontend API keys)
- ⚠️ KB injection in system prompt (needs packaging/caching + privacy stance)
- ⚠️ Fill-in-the-middle format (stop tokens + truncation policy must support multi-line blocks)
- ⚠️ Debounced auto-trigger (1500ms) (configurable; recommend tuning guidance)

---

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| Multi-line scope | ADR-0043:112-114, ST-08-14:12,135-137 | Multi-line completions explicitly in scope; AC and tests added |
| API key config | ADR-0043:127, ref-ai-completion:203, ST-08-14:95 | `OPENAI_LLM_COMPLETION_API_KEY` added to all config blocks |
| Rate limiting aligned | ADR-0043:190-191, ST-08-14:150 | Clarified as "follow-up if not in MVP" |
| Stop tokens | ADR-0043:116, ref-ai-completion:112 | Simplified to triple backticks; restrictive tokens removed |
| Truncation policy | ADR-0043:118-119, ref-ai-completion:66-67,86, ST-08-14:18 | Discard `finish_reason="length"`, return empty |
| KB packaging | ADR-0043:193, ref-ai-completion:129-133 | Production packaging, memory cache, fallback behavior defined |
| Keymap precedence | ref-ai-completion:182-185 | Tab/Escape override `indentWithTab` when ghost text visible |
| Privacy/logging | ADR-0043:194, ref-ai-completion:244-245 | Never log code/prompts; third-party risks documented |
