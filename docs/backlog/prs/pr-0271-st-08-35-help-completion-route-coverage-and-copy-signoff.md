---
type: pr
id: PR-0271
title: "ST-08-35: help completion route coverage and copy signoff"
status: ready
owners: "agents"
created: 2026-04-20
updated: 2026-04-20
stories:
  - "ST-08-35"
tags: ["frontend", "ux", "docs", "accessibility", "copy"]
dependencies:
  - "EPIC-08"
  - "ST-11-19"
  - "ST-08-34"
acceptance_criteria:
  - "Given help copy needs product-owner approval, when this slice starts, then `docs/reference/ref-skriptoteket-help-copy-signoff.md` is created or updated with the route/topic copy plan before any production topic wording is changed."
  - "Given the route table in `frontend/apps/skriptoteket/src/router/routes.ts`, when tests run, then every named route is covered by the help topic catalog or explicitly documented as intentionally using a generic fallback."
  - "Given the help drawer is opened from authenticated and unauthenticated chrome, when Escape, backdrop click, route changes, and opener focus restoration are tested, then behavior is deterministic and accessible."
  - "Given role-specific navigation, when the help index renders under user, contributor, admin, and superuser roles, then topics match available surfaces and do not expose unavailable admin/contributor entries."
  - "Given the first approved copy batch exists, when topic components are updated, then implemented Swedish copy matches the approved reference without ad hoc wording changes."
  - "Given the help drawer is a secondary reading surface, when it renders, then it uses a calm design-system off-white surface and nested help-index link lists use borders/dividers without their own brutal shadows."
  - "Given field-level help is added, when suggestion, tool-run, admin-decision, and editor fields need explanations, then they share one reusable micro-help component/pattern."
---

## Problem

The SPA help framework exists and is lazy-loaded, but it is not yet complete
against the current route table. Some topics are shallow, some routes have no
topic, micro-help patterns are inconsistent, and early EPIC-08 help docs still
describe retired SSR templates.

The larger product risk is copy drift: if implementation fills topic components
directly, the exact Swedish help wording becomes hard to review. The next slice
therefore must front-load a copy signoff reference before final topic wording is
implemented.

## Goal

Create a durable SPA help completion plan and implementation lane:

- use `docs/reference/ref-skriptoteket-help-copy-signoff.md` as the exact copy
  approval surface
- make route coverage explicit and testable through a help topic catalog
- harden the drawer interaction/accessibility behavior
- add missing high-traffic topics after copy approval
- extract one shared micro-help pattern for field-level explanations

## Non-goals

- Do not replace the SPA help framework with a backend-driven CMS.
- Do not implement unapproved Swedish copy in topic components.
- Do not change HuleEdu-owned auth lifecycle ceremonies.
- Do not add walkthroughs, search, video, analytics, or AI-generated help.
- Do not rewrite Klassrumskartan help outside the guide/generator path.

## Implementation Plan

1. **Copy signoff reference first**
   - Update `docs/reference/ref-skriptoteket-help-copy-signoff.md` with the
     first batch of exact Swedish drawer copy and field micro-help.
   - Mark each block `draft`, `approved`, `revise`, or `superseded`.
   - Stop before production wording changes if the first batch is not approved.

2. **Help topic catalog**
   - Add a catalog module, for example
     `frontend/apps/skriptoteket/src/components/help/helpTopicCatalog.ts`.
   - Move topic metadata into the catalog: topic id, title, route names, index
     section, minimum role, loader, and fallback notes.
   - Derive route-topic resolution and index entries from the catalog where
     practical.
   - Add a focused test that compares catalog route names with
     `router/routes.ts`.

3. **Drawer behavior hardening**
   - Add deterministic Escape handling.
   - Restore focus to the opener when the drawer closes.
   - Decide and test the non-modal drawer behavior for outside click/focus and
     route changes.
   - Keep the drawer visually calm: one outer shadow only, design-system
     off-white surface, and border/divider treatment for nested help-index
     lists.
   - Keep `Teleport` and async topics; no new dependency is needed.

4. **Approved topic coverage**
   - Add or expand topics only after the relevant copy block is approved.
   - First batch should cover auth lifecycle/provisioning, catalog/tool
     run/result, profile, vault, my runs, suggestions, admin suggestions/tools,
     editor, forbidden, and route recovery.
   - Keep `apps_detail` as a generic fallback; use context topics for rich apps
     such as Klassrumskartan.

5. **Micro-help pattern**
   - Extract a reusable field-level help popover or disclosure component.
   - Migrate `SuggestionNewView` description help first.
   - Add approved micro-help to tool run file inputs, suggestion title/body,
     admin decision rationale, and editor fields.

6. **Docs cleanup**
   - Update EPIC-08 to list ST-08-35 as the active SPA help completion story.
   - Leave historical ST-08-04 through ST-08-09 docs intact unless a separate
     docs cleanup slice explicitly supersedes them.
   - Record live UI proof in `.codex/handoff.md` for any route/UI behavior
     changes.

## Test Plan

- `pdm run fe-test -- --run src/components/help/HelpPanel.spec.ts`
- Focused catalog coverage test, for example:
  `pdm run fe-test -- --run src/components/help/helpTopicCatalog.spec.ts`
- Focused micro-help component tests once the shared component exists.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Live browser proof on `http://127.0.0.1:5173/` for desktop and mobile widths:
  open help, navigate, close via Escape/backdrop, verify role-aware index and at
  least one approved topic from each first-batch surface.
- `pdm run docs-validate`
- `pdm run handoff-validate` if `.codex/handoff.md` changes.
- `git diff --check`

## Rollback Plan

Revert the help catalog and component changes while keeping the copy signoff
reference as retained planning history if the wording process remains useful.
If drawer behavior causes regressions, restore the previous click-to-toggle and
backdrop-close behavior and keep route coverage tests for the next attempt.

## Implementation Notes

- Use the existing Vue 3 stack and patterns; Context7 confirms `Teleport` and
  `defineAsyncComponent` remain appropriate for this shape.
- Keep files under the repo size budget. The current help modules are already
  split below the threshold, and the catalog should stay small and typed.
- Treat the help copy reference as the source of product wording. Component
  tests should assert approved copy only after signoff.
