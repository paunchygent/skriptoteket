---
type: epic
id: EPIC-08
title: "Contextual help (Hjälp) and onboarding"
status: active
owners: "agents"
created: 2025-12-17
updated: 2026-01-07
outcome: "Users understand what they can do on each page via concise, Swedish, context-aware help without external documentation."
---

## Scope

- Add a **global, collapsible** “Hjälp” entry point that is available both **before and after login**.
- Provide **context-aware help content** per page (and per role where relevant).
- Provide a **help index** with navigation back to the index from any page’s help (“Till hjälpindex”).
- Add **field-level micro-help**:
  - discrete help icons next to non-trivial fields
  - short, action-focused explanations (Swedish, no technical jargon)
  - examples via placeholder/ghost text that disappears as the user types
- Keep the implementation **minimal and consistent with the SPA** (Vue/Vite, existing UI patterns/tokens; avoid new heavy
  dependencies).
- Add **in-editor intelligence** for the script editor (CodeMirror 6 extensions for autocomplete, lint, hover docs).
- Add **AI-powered inline completions** (Copilot-style ghost text) with backend LLM proxy.
- Add a **chat-first AI assistant** in the script editor that can propose deterministic CRUD edits (insert/replace/delete)
  with **diff preview + explicit apply/undo**, and privacy-safe metadata-only observability (no prompt/code logging).
- Accessibility baseline: keyboard operable, reasonable ARIA, close-on-escape, does not trap focus.

## Stories

- [ST-08-01: Help framework (toggle + index + behavior)](../stories/story-08-01-help-framework.md)
- [ST-08-02: Login help + micro-help](../stories/story-08-02-login-help.md)
- [ST-08-03: Post-login home help index (site map)](../stories/story-08-03-home-help-index.md)
- [ST-08-04: Catalog help (browse + run)](../stories/story-08-04-catalog-help.md)
- [ST-08-05: Tool results + downloads help](../stories/story-08-05-results-and-downloads-help.md)
- [ST-08-06: Contributor help (Mina verktyg + Föreslå skript)](../stories/story-08-06-contributor-help.md)
- [ST-08-07: Admin help (Förslag + Verktyg)](../stories/story-08-07-admin-dashboard-help.md)
- [ST-08-08: Script editor help (overview + versioning)](../stories/story-08-08-editor-help-overview.md)
- [ST-08-09: Script editor help (test runner + run result)](../stories/story-08-09-editor-help-test-area.md)
- [ST-08-10: Script editor intelligence Phase 1 - Discoverability MVP](../stories/story-08-10-script-editor-intelligence.md)
- [ST-08-11: Script editor intelligence Phase 2 - Contract + security](../stories/story-08-11-script-editor-intelligence-phase2.md)
- [ST-08-12: Script editor intelligence Phase 3 - Best practices](../stories/story-08-12-script-editor-intelligence-phase3.md)
- [ST-08-13: Tool usage instructions](../stories/story-08-13-tool-usage-instructions.md)
- [ST-08-14: AI inline completions MVP](../stories/story-08-14-ai-inline-completions.md)
- [ST-08-15: Contract lint rule IDs (AI signal)](../stories/story-08-15-contract-lint-source-ids.md)
- [ST-08-16: AI edit suggestions MVP](../stories/story-08-16-ai-edit-suggestions.md)
- [ST-08-17: Tabby edit suggestions + prompt A/B evaluation](../stories/story-08-17-tabby-edit-suggestions-ab-testing.md)
- [ST-08-18: AI prompt system v1 (templates + contract fragments + validation)](../stories/story-08-18-ai-prompt-system-v1.md)
- [ST-08-19: AI prompt evaluation harness (live backend + llama.cpp)](../stories/story-08-19-ai-prompt-eval-harness-live-backend.md)
- [ST-08-20: Editor AI chat drawer MVP (beginner-friendly assistant UI)](../stories/story-08-20-editor-ai-chat-drawer-mvp.md)
- [ST-08-21: AI structured CRUD edit ops protocol v1 (insert/replace/delete)](../stories/story-08-21-ai-structured-crud-edit-ops-protocol-v1.md)
- [ST-08-22: Editor AI proposed changes diff preview + apply/undo](../stories/story-08-22-editor-ai-diff-preview-apply-undo.md)
- [ST-08-23: AI editor chat streaming proxy + LLM_CHAT_* config](../stories/story-08-23-ai-chat-streaming-proxy-and-config.md)

## Implementation Summary (as of 2026-01-07)

- AI inline completions (ghost text) are live with backend LLM proxy and CodeMirror integration (ST-08-14).
- AI edit suggestions are live in the editor with preview + apply flow (ST-08-16).
- Prompt system v1 is in place: template registry, contract fragments, budget validation, and template ID logging (ST-08-18).
- Live prompt evaluation harness exists with metadata-only artifacts under `.artifacts/ai-prompt-eval/` (ST-08-19).
- Editor AI chat backend is in place: tool-scoped SSE endpoint + canonical server-side chat thread stored in `tool_session_messages` (per `{user_id, tool_id}`) with TTL enforced on access and sliding-window budgeting (ST-08-23).
- Remaining work:
  - Tabby provider switch + prompt A/B evaluation for edit suggestions (ST-08-17).
  - Chat-first editor AI UX (drawer + structured CRUD edits + diff preview + apply/undo) (ST-08-20/21/22).

## Risks

- Help becomes too verbose or visually noisy (mitigate: short copy, progressive disclosure, discrete icons).
- Copy drift across pages (mitigate: centralized patterns + “source of truth” per story).
- Accessibility regressions (mitigate: keyboard/escape/outside-click close, aria-controls/expanded).
- Maintenance overhead as features evolve (mitigate: keep help content near templates/routes it describes).
- AI UX trust: if previews are unclear or edits apply unexpectedly, users will stop using the feature (mitigate: diff
  preview + atomic apply + easy undo + explicit scope indicators).

## Dependencies

- EPIC-05 (HuleEdu design system) for consistent styling.
- ST-05-07 for stabilized layout primitives (panel width + dvh fallback) if needed before polishing the help drawer.
- ST-11-12 (Script editor migration) for CodeMirror 6 base setup.
- EPIC-14 editor foundations that the AI UX builds on:
  - ST-14-11/12 (sandbox debug details + copy bundle)
  - ST-14-17 (diff viewer primitive)

## ADRs

- [ADR-0035: Script editor intelligence architecture](../../adr/adr-0035-script-editor-intelligence-architecture.md)
- [ADR-0036: Tool usage instructions architecture](../../adr/adr-0036-tool-usage-instructions.md)
- [ADR-0043: AI completion integration](../../adr/adr-0043-ai-completion-integration.md)
- [ADR-0050: Self-hosted LLM infrastructure](../../adr/adr-0050-self-hosted-llm-infrastructure.md)
- [ADR-0051: Chat-first AI editing](../../adr/adr-0051-chat-first-ai-editing.md)
- [ADR-0052: LLM prompt budgeting + KB fragments](../../adr/adr-0052-llm-prompt-budgets-and-kb-fragments.md)
