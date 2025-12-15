---
type: epic
id: EPIC-05
title: "HuleEdu design system harmonization"
status: done
owners: "agents"
created: 2025-12-15
outcome: "Skriptoteket frontend uses HuleEdu design tokens and Brutalist styling, ensuring visual consistency for future HuleEdu integration."
---

## Scope

This epic applies the HuleEdu design system across all Skriptoteket web templates:

- **Design tokens integration**: CSS custom properties for colors, typography, spacing, shadows
- **Template migration**: Update all templates to use HuleEdu component classes
- **HTMX UX enhancements**: Loading states, toast notifications, form improvements (per REF-htmx-ux-enhancement-plan)
- **CodeMirror theming**: Style code editor to match design language

## Stories

- [ST-05-01: CSS foundation and base template](../stories/story-05-01-css-foundation.md) (DONE)
- [ST-05-02: Simple template migration](../stories/story-05-02-simple-templates.md) (DONE)
- [ST-05-03: Browse template migration](../stories/story-05-03-browse-templates.md) (DONE)
- [ST-05-04: Suggestion template migration](../stories/story-05-04-suggestion-templates.md) (DONE)
- [ST-05-05: Admin template migration](../stories/story-05-05-admin-templates.md) (DONE)
- [ST-05-06: HTMX loading and toast enhancements](../stories/story-05-06-htmx-enhancements.md)

## Risks

- Design token updates in HuleEdu may require Skriptoteket updates (mitigate: version tokens file)
- Google Fonts CDN dependency (mitigate: fallback to system fonts in font stack)
- Template migration may reveal inconsistent markup patterns (mitigate: standardize during migration)

## Dependencies

- ADR-0001 (server-driven HTMX UI approach)
- ADR-0017 (HuleEdu design system adoption)
- REF-htmx-ux-enhancement-plan (implementation guide)
- EPIC-04 ST-04-03 (admin script editor - already exists, styling applied here)
