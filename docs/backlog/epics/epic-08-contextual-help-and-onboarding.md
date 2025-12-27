---
type: epic
id: EPIC-08
title: "Contextual help (Hjälp) and onboarding"
status: proposed
owners: "agents"
created: 2025-12-17
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
- Keep the implementation **vanilla** (server-rendered templates + HTMX where helpful, plain CSS/JS, no new dependencies).
- Add **in-editor intelligence** for the script editor (CodeMirror 6 extensions for autocomplete, lint, hover docs).
- Add **AI-powered inline completions** (Copilot-style ghost text) with backend LLM proxy.
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

## Risks

- Help becomes too verbose or visually noisy (mitigate: short copy, progressive disclosure, discrete icons).
- Copy drift across pages (mitigate: centralized patterns + “source of truth” per story).
- Accessibility regressions (mitigate: keyboard/escape/outside-click close, aria-controls/expanded).
- Maintenance overhead as features evolve (mitigate: keep help content near templates/routes it describes).

## Dependencies

- EPIC-05 (HuleEdu design system) for consistent styling.
- ST-05-07 for stabilized layout primitives (panel width + dvh fallback) if needed before polishing the help drawer.
- ST-11-12 (Script editor migration) for CodeMirror 6 base setup.

## ADRs

- [ADR-0035: Script editor intelligence architecture](../../adr/adr-0035-script-editor-intelligence-architecture.md)
- [ADR-0036: Tool usage instructions architecture](../../adr/adr-0036-tool-usage-instructions.md)
- [ADR-0043: AI completion integration](../../adr/adr-0043-ai-completion-integration.md)
