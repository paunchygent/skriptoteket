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
- [ST-08-10: Script editor intelligence (CodeMirror 6 linting and suggestions)](../stories/story-08-10-script-editor-intelligence.md)

## Risks

- Help becomes too verbose or visually noisy (mitigate: short copy, progressive disclosure, discrete icons).
- Copy drift across pages (mitigate: centralized patterns + “source of truth” per story).
- Accessibility regressions (mitigate: keyboard/escape/outside-click close, aria-controls/expanded).
- Maintenance overhead as features evolve (mitigate: keep help content near templates/routes it describes).

## Dependencies

- EPIC-05 (HuleEdu design system) for consistent styling.
- ST-05-07 for stabilized layout primitives (panel width + dvh fallback) if needed before polishing the help drawer.
