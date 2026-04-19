---
type: story
id: ST-08-35
title: "Help completion: route coverage, behavior hardening, and copy signoff"
status: ready
owners: "agents"
created: 2026-04-20
epic: "EPIC-08"
dependencies:
  - "ST-11-19"
  - "ST-08-34"
acceptance_criteria:
  - "Given the SPA route table changes, when help coverage is validated, then every named route is either mapped to a help topic or explicitly marked as intentionally generic/unsupported in a tested catalog."
  - "Given Swedish help copy is product-facing, when implementation begins, then exact word-by-word topic copy is first drafted in `docs/reference/ref-skriptoteket-help-copy-signoff.md` and approved before Vue topic components are updated."
  - "Given a user opens the help panel, when they press Escape, click outside, navigate, or continue interacting with the app, then help closes or resynchronizes according to the documented drawer behavior without trapping focus."
  - "Given logged-in roles differ, when the help index renders, then users only see topics relevant to their available role surfaces."
  - "Given high-traffic routes such as auth lifecycle, catalog, tool runs/results, profile, vault, my runs, contributor, admin, and recovery pages, when help opens, then the topic content is concise, Swedish, action-focused, and matches the approved copy reference."
  - "Given the help drawer is opened, when the index renders inside it, then the drawer uses a calm design-system off-white surface and nested link lists do not add brutal shadows."
  - "Given non-trivial fields need contextual help, when micro-help is added, then it uses one shared accessible pattern instead of one-off popovers."
ui_impact: "Yes (global help drawer content, behavior, index coverage, and field-level micro-help)"
data_impact: "No"
risks:
  - "Copy drift if implementation proceeds before signoff."
  - "Drawer behavior regressions on mobile or immersive app routes."
  - "Overly broad help text that makes the drawer noisy."
---

## Context

The active Skriptoteket help feature is the SPA help framework implemented by
ST-11-19 and refined for Klassrumskartan by ST-08-34. The current framework is
sound: it uses global help state, a lazy-loaded drawer, async topic components,
role-aware index sections, and context-first topic selection for
Klassrumskartan.

The remaining work is now less about inventing a new help system and more about
closing the gaps:

- route coverage is incomplete
- several topics are only shallow placeholders
- field-level micro-help is inconsistent across surfaces
- drawer close/focus behavior needs explicit tests
- drawer visual treatment needs to stay calm and avoid nested brutal shadows
- older EPIC-08 help docs still reference retired SSR templates and do not
  reflect the SPA route table
- exact Swedish copy needs product-owner signoff before being baked into Vue
  topic components

## Scope

- Create and maintain a help topic catalog that makes route coverage explicit.
- Draft exact Swedish help copy in
  `docs/reference/ref-skriptoteket-help-copy-signoff.md` before implementation.
- Add or expand route topics for missing auth, profile, vault, my runs,
  contributor, admin, public, and recovery surfaces.
- Harden drawer behavior for Escape, outside interaction, route changes, focus
  restoration, and mobile layout.
- Keep the help drawer surface visually quiet and apply brutal shadow only to
  the outer drawer, not nested index lists.
- Extract a shared field-level micro-help pattern and migrate the first
  high-value fields onto it.
- Keep Klassrumskartan mode help generated from the existing getting-started
  guide unless the guide itself changes.

## Out of Scope

- Interactive product tours.
- Search within help.
- Video help content.
- AI-generated runtime help content.
- Backend APIs for help content.
- Changing HuleEdu-owned auth lifecycle behavior.

## Current Implementation Map

- Help state and route/context resolution:
  `frontend/apps/skriptoteket/src/components/help/useHelp.ts`
- Async topic registry:
  `frontend/apps/skriptoteket/src/components/help/helpTopics.ts`
- Drawer shell:
  `frontend/apps/skriptoteket/src/components/help/HelpPanel.vue`
- Role-aware index:
  `frontend/apps/skriptoteket/src/components/help/HelpIndex.vue`
- Topic components:
  `frontend/apps/skriptoteket/src/components/help/topics/`
- Klassrumskartan guide source:
  `docs/guides/guide-klassrumskartan-kom-igang.md`
- Planner help generator:
  `scripts/generate_planner_help.py`

## Notes

- Vue 3 `Teleport` and `defineAsyncComponent` remain the right primitives for
  the help drawer and lazy topic loading. Context7 was checked during planning;
  no new dependency is needed.
- The help copy reference is the signoff gate. If a topic is not approved there,
  implementation should add structure/tests only, not final Swedish wording.
- Existing ST-08-04 through ST-08-09 story docs are retained as historical
  intent but point at retired SSR files. This story is the SPA completion story
  for the current route table.
