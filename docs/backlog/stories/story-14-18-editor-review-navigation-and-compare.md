---
type: story
id: ST-14-18
title: "Editor: review navigation improvements (compare targets + deep links)"
status: ready
owners: "agents"
created: 2025-12-29
updated: 2026-01-04
epic: "EPIC-14"
acceptance_criteria:
  - "Given a reviewer is in an in_review version, when opening compare, then the UI selects a sensible default target: (1) current published (active) version if the tool is published, else (2) most recent rejected review (archived + reviewed_at set + published_at null) if available, else (3) derived_from_version_id if present, else (4) previous visible version."
  - "Given an author is in a draft version, when opening compare, then the UI selects the immediate parent version (derived_from_version_id) if present, else the previous visible version."
  - "Given the reviewer shares a link, then compare state can be deep-linked via query params without leaking access."
  - "Given the compare view will be used as a safe preview surface for multiple workflows (review now, AI later), when compare state is deep-linked, then the URL also captures which field is being compared (code vs schemas vs instructions)."
  - "Given there are unsaved changes, then switching base versions prompts for confirmation, but switching only compare target/field does not."
  - "Given the editor has a working copy (unsaved buffers), then compare can target the working copy, and deep-links do not leak access (unavailable working copy is handled explicitly)."
  - "Given saving always creates a new version (draft snapshot), then the primary save CTA label is explicit about whether it creates a new draft version or creates a new draft from a non-draft version."
dependencies:
  - "ST-14-17"
ui_impact: "Yes"
data_impact: "No"
---

## Notes

AI alignment: make compare deep-links field-aware so future AI flows can direct users to the relevant diff (e.g. ‘code changes’).

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

## Implementation decisions

- Compare mode is full-width inside the editor workspace (not a narrow drawer), since diff ergonomics depends on width.
- Compare state is deep-linkable via query params and field-aware, e.g.:
  - `version=<baseVersionId>` (existing behavior; selects the base version to open)
  - `compare=<targetVersionId|working>` (target can be a version id or the local working copy)
  - `field=<code|entrypoint|settings_schema|input_schema|instructions>`
- The editor must not reload or lose unsaved buffers when changing only `compare`/`field`.
  - **Decided:** editor data loading must watch only the base selection key (toolId/versionId/query.`version`) or the resolved editor API path; `compare`/`field` are client-only state and must not trigger reloads.
  - Base version switches (including `version=` changes) still prompt when there are unsaved changes.
- Working copy compare target:
  - Until ST-14-30 ships, `compare=working` refers to the in-memory editor buffers only.
  - **Implementation requirement:** keep the “working copy” access behind a small `getWorkingCopy()`/provider abstraction so ST-14-30 can plug in async IndexedDB restore/loading without changing the compare view contract.
- Default compare target rules:
  - In review (`in_review`): active published version if available; else most recent rejected review (archived + reviewed_at set + published_at null); else derived_from_version_id; else previous visible.
  - Draft: immediate parent (derived_from_version_id); else previous visible.
- **Decided API shape:** extend the editor boot response `versions[]` summary with the minimal metadata needed to compute defaults reliably:
  - `reviewed_at` (nullable)
  - `published_at` (nullable)
  - Use `EditorBootResponse.derived_from_version_id` for the currently loaded base version (no need to duplicate it in each version summary).
- Save CTA labels must be explicit (no misleading “Spara” when Save always creates a new version):
  - When editing a draft (save_mode=snapshot): primary CTA should communicate “new draft version” (e.g. “Spara ny utkastversion”).
  - When viewing a non-draft (save_mode=create_draft): primary CTA should communicate “create draft” (e.g. “Skapa nytt utkast”).
- Follow-up UX: Focus mode (collapse left sidebar) is tracked separately in ST-14-31 and is planned immediately after this story.
