---
type: story
id: ST-32-07
title: "Public landing entry hierarchy and mockup-grounded CTA cutover"
status: ready
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
epic: "EPIC-32"
dependencies:
  ["ADR-0027", "ADR-0032", "ADR-0079", "ST-11-21", "ST-32-06"]
acceptance_criteria:
  - "Given an unauthenticated visitor opens `/`, when the landing page renders, then the header and hero expose one obvious public entry into Klassrumskartan at `/public/apps/classroom.group-seating-studio` without forcing login first."
  - "Given this story contains layout-heavy landing-page changes, when any implementation slice starts, then the assigned developer has first reviewed `.agents/rules/045-huleedu-design-system.md`, the `skriptoteket-frontend-specialist` skill, and the `brutalist-academic-ui` skill, and has iterated on a story-scoped mockup under `docs/mockups/` before production Vue code changes."
  - "Given the public Klassrumskartan route is the strongest public entry Skriptoteket currently has, when the hero CTA row renders, then the public app is the primary action while `Skapa konto` and `Logga in` remain available as clearly secondary paths."
  - "Given both the header and hero render above the fold, when this story ships, then the header-level `Klassrumskartan` affordance remains a quiet discoverability/navigation link while the hero remains the single primary action surface."
  - "Given the landing page must stay within the established product language, when the header and hero are redesigned, then the implementation follows the approved mockup and preserves the existing Skriptoteket/HuleEdu brutalist-academic design primitives rather than inventing a separate marketing-site aesthetic."
  - "Given all Swedish landing copy in this story is user-facing product language, when implementation begins and ships, then every sentence is treated as draft until explicit user sign-off and must stay short, conversational, verb-led, non-technical, and free of sales language, internal feature language, or implementation detail."
ui_impact: "Yes (landing header and hero CTA hierarchy)"
data_impact: "No"
---

## Context

Skriptoteket now has one real public curated app, Klassrumskartan, but the current unauthenticated
landing still behaves as if authentication is the only meaningful next step.

This story fixes the first decision surface. The header and hero must make public entry into
Klassrumskartan obvious before the visitor is asked to create an account or log in.

## Notes

- Public Klassrumskartan is a real usage path, not a throwaway demo or teaser. Copy and CTA
  hierarchy should reflect that.
- The primary unauthenticated action should become "open the public app now", while `Skapa konto`
  and `Logga in` remain available as secondary or tertiary paths.
- The header-level `Klassrumskartan` entry is quiet discoverability nav, not a second primary CTA.
  The hero owns the only strong primary action above the fold.
- Calm the header. Do not duplicate `Logga in` as a competing strong header action when the hero
  already owns the main CTA hierarchy.
- Layout-heavy slices under this story must stay grounded in the current HuleEdu/Skriptoteket
  design language. Do not invent a separate marketing-site aesthetic or startup-style visual
  language.
- Avoid card-first organization. Do not default to cards, and do not use nested cards. Prefer
  typographic grouping, hard dividers, rails, ruled sections, asymmetric columns, image-and-text
  composition, and whitespace structure before reaching for cards.
- Mockup-first planning is required here, not optional polish. Follow the precedent from
  `PR-0184`: use `docs/mockups/` to align on header, hero, section order, CTA hierarchy, and
  preview language before touching production Vue components.
- `PR-0237` is now decided: `docs/mockups/st-32-07-public-landing-discoverability/designer-a.html`
  is the winning submission, and the separate canonical blueprint copy for follow-on work is
  `docs/mockups/st-32-07-public-landing-discoverability/index.html`. Carry that direction into
  `PR-0238` with light polish rather than a reopened layout debate.
- All Swedish copy in this story is provisional until the user signs it off. Draft copy should aim
  for normal conversational Swedish in full sentences, short and clear, with no internal jargon,
  no compressed technical phrasing, and no salesman language.
- `ST-32-06` stays closed as the shipped public-workspace adoption proof. This follow-up story owns
  the landing entry hierarchy only. Do not let it turn into a catch-all for later public-entry
  concerns.

## Planned PR slices

- [PR-0237: ST-32-07 landing public-entry information architecture and canonical mockup preview](../prs/pr-0237-st-32-07-landing-public-entry-information-architecture-and-canonical-mockup-preview.md)
- [PR-0238: ST-32-07 landing header and hero public-entry cutover](../prs/pr-0238-st-32-07-landing-header-and-hero-public-entry-cutover.md)

## References

- Epic parent:
  [EPIC-32](../epics/epic-32-public-curated-app-access-foundation-and-klassrumskartan-demo.md)
- Public curated-app boundary:
  [ADR-0079](../../adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md)
- Current auth-adaptive home surface:
  [ST-11-21](story-11-21-unified-landing-page.md)
- Shipped public Klassrumskartan baseline:
  [ST-32-06](story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md)
- Follow-on showcase surface:
  [ST-32-08](story-32-08-featured-public-app-showcase-and-authenticated-value-previews.md)
- Follow-on route recovery:
  [ST-32-09](story-32-09-canonical-public-route-recovery-and-spa-unmatched-state.md)
- Design-system rule:
  [045-huleedu-design-system.md](../../../.agents/rules/045-huleedu-design-system.md)
