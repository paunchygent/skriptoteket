---
type: review
id: REV-EPIC-08
title: "Review: AI Completion Integration for EPIC-08"
status: pending
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
| OpenAI-compatible API | Supports Ollama (free/local), OpenRouter, OpenAI without vendor lock-in | [ ] |
| Backend proxy (no frontend API keys) | Security: API keys never exposed to browser | [ ] |
| KB injection in system prompt | Ensures suggestions follow runner constraints, Contract v2 | [ ] |
| Fill-in-the-middle format | Standard approach for code completion prompts | [ ] |
| Debounced auto-trigger (1500ms) | Balances responsiveness vs API load | [ ] |

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
**Date:** YYYY-MM-DD
**Verdict:** pending

### Required Changes

[To be filled by reviewer]

### Suggestions (Optional)

[To be filled by reviewer]

### Decision Approvals

- [ ] OpenAI-compatible API
- [ ] Backend proxy (no frontend API keys)
- [ ] KB injection in system prompt
- [ ] Fill-in-the-middle format
- [ ] Debounced auto-trigger (1500ms)

---

## Changes Made

[Author fills this in after addressing feedback]

| Change | Artifact | Description |
|--------|----------|-------------|
