---
type: story
id: ST-32-08
title: "Featured public-app showcase and authenticated-value previews"
status: ready
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
epic: "EPIC-32"
dependencies:
  ["ADR-0027", "ADR-0032", "ADR-0079", "ST-11-21", "ST-32-06", "ST-32-07"]
acceptance_criteria:
  - "Given the public Klassrumskartan route is now the only publicly available app surface, when the landing page scrolls below the fold, then a featured showcase demonstrates what the app actually lets a teacher do in practice instead of relying only on generic value-proposition cards."
  - "Given some Skriptoteket capabilities remain authenticated-only, when the landing page presents them, then they appear as clearly labeled showcase or preview surfaces rather than misleading public entry points."
  - "Given this story changes visually important landing sections, when implementation starts, then the assigned developer has first reviewed `.agents/rules/045-huleedu-design-system.md`, the `skriptoteket-frontend-specialist` skill, and the `brutalist-academic-ui` skill, and follows the approved mockup/IA direction from `ST-32-07`."
  - "Given this story extends the landing page below the fold, when implementation begins and ships, then all Swedish copy is treated as draft until explicit user sign-off and stays short, conversational, verb-led, non-technical, and free of sales language or internal product terminology."
  - "Given this story is layout-heavy, when the showcase sections are designed, then they do not default to cards or nested cards and instead prefer stronger structural layout devices such as section rules, type hierarchy, columns, media framing, and deliberate spacing."
ui_impact: "Yes (below-the-fold landing showcase and authenticated-only preview sections)"
data_impact: "No"
---

## Context

The current landing page still tells visitors that Skriptoteket is valuable more than it shows that
value. That is weaker now that Klassrumskartan can already be used directly.

This story converts the tell-heavy below-the-fold landing narrative into a show-first product
surface.

## Notes

- The featured section should show real app use, not a vague “platform benefits” summary.
- Authenticated-only value may still be showcased, but it must be labeled clearly so visitors do
  not mistake it for another public route.
- This story depends on the IA and CTA hierarchy work from `ST-32-07`; it should not reopen header
  or hero structure debates.
- Do not use cards as the default organizing device, and do not stack or nest them. The landing
  page should feel editorial and structural rather than mobile-first/generic.
- All Swedish copy remains provisional until the user signs it off sentence by sentence.
- Keep the page compact and product-grounded. One strong featured public-app section plus one
  authenticated-value preview section is enough.

## Planned PR slices

- [PR-0239: ST-32-08 featured public-app showcase and authenticated-value preview surfaces](../prs/pr-0239-st-32-08-featured-public-app-showcase-and-authenticated-value-preview-surfaces.md)

## References

- Epic parent:
  [EPIC-32](../epics/epic-32-public-curated-app-access-foundation-and-klassrumskartan-demo.md)
- Public entry hierarchy prerequisite:
  [ST-32-07](story-32-07-public-landing-entry-hierarchy-and-mockup-grounded-cta-cutover.md)
- Shipped public Klassrumskartan baseline:
  [ST-32-06](story-32-06-klassrumskartan-demo-adoption-on-the-public-browser-workspace-profile.md)
