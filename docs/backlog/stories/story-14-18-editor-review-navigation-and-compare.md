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
  - "Given a reviewer is in an in_review version, when opening compare, then the UI selects a sensible default target: (1) current published (active) version if the tool is published, else (2) most recent rejected review (archived + reviewed_at set + published_at null) if available, else (3) parent_version_id if present, else (4) previous visible version."
  - "Given an author is in a draft version, when opening compare, then the UI selects the immediate parent version (parent_version_id) if present, else the previous visible version."
  - "Given the reviewer shares a link, then compare state can be deep-linked via query params without leaking access."
  - "Given the compare view will be used as a safe preview surface for multiple workflows (review now, AI later), when compare state is deep-linked, then the URL also captures which virtual file is being compared via field=tool.py, entrypoint.txt, settings_schema.json, input_schema.json, usage_instructions.md."
  - "Given there are unsaved changes, then switching base versions prompts for confirmation, but switching only compare target/field does not."
  - "Given the editor has a working copy (unsaved buffers), then compare can target the working copy head (compare=working), and deep-links do not leak access (missing working copy is handled explicitly)."
  - "Given the URL changes only compare/field, then the editor does not refetch boot data and does not reset any unsaved buffers."
  - "Given saving always creates a new version (draft snapshot), then the primary save CTA label is explicit about whether it creates a new draft version or creates a new draft from a non-draft version."

dependencies:
  - "ST-14-17"
  - "ST-14-30"

ui_impact: "Yes"
data_impact: "No"
---

## Notes

AI alignment: make compare deep-links virtual-file-aware so future AI flows
can direct users to the relevant diff (e.g. `field=tool.py`).

Reference: `docs/reference/ref-tool-editor-dx-review-2025-12-29.md`

See also:

- Diff viewer primitive: `docs/backlog/stories/story-14-17-editor-version-
diff-view.md`
- Working copy + checkpoints: `docs/backlog/stories/story-14-30-editor-
working-copy-persistence-indexeddb.md`
- Focus mode (width): `docs/backlog/stories/story-14-31-editor-focus-mode-
collapse-sidebar.md`

## Implementation decisions

- Compare mode is full-width inside the editor workspace (not a narrow
  drawer), since diff ergonomics depends on width.
- Compare state is deep-linkable via query params and virtual-file-aware.
  - Base selection:
    - `/admin/tools/:toolId?version=<baseVersionId>` selects the base version
      (optional; if omitted, backend default applies).
    - `/admin/tool-versions/:baseVersionId` selects the base version via the
      path param; `version=` MUST be ignored/removed to avoid “URL ≠ loaded version”
      ambiguity.
  - Compare selection:
    - `compare=<targetVersionId|working>` (target can be a version id or the
      local working copy head)
    - `field=<tool.py|entrypoint.txt|settings_schema.json|input_schema.json|
usage_instructions.md>`
- The editor must not reload or lose unsaved buffers when changing only
  `compare`/`field`.
  - **REQUIRED:** editor boot reload triggers MUST exclude `compare` and
    `field`.
  - Practical guardrail: do not use `route.fullPath` as an editor reload key.
  - Base version switches still prompt when there are unsaved changes.
- Working copy compare target:
  - `compare=working` refers to the persisted IndexedDB-backed working copy
    head (ST-14-30).
  - **Implementation requirement:** keep the “working copy” access behind a
    small `getWorkingCopy()`/provider abstraction so the compare view can treat it
    as a single “text blob source” even if retrieval is async.
- Default compare target rules:
  - In review (`in_review`): active published version if available; else most
    recent rejected review (archived + reviewed_at set + published_at null); else
    `parent_version_id`; else previous visible.
  - Draft: immediate parent `parent_version_id`; else previous visible.
- **Decided API shape (boot response):**
  - Extend `versions[]` summaries with the minimal metadata needed to compute
    defaults reliably:
    - `reviewed_at` (nullable)
    - `published_at` (nullable)
  - Split the overloaded “derived from” semantics into two explicit fields:
    - `parent_version_id`: the selected version’s lineage pointer (domain
      `tool_versions.derived_from_version_id`), nullable.
    - `create_draft_from_version_id`: the version id a “Skapa nytt utkast”
      action should derive from when `save_mode=create_draft`, nullable.
- Save CTA labels must be explicit (no misleading “Spara” when Save always
  creates a new version):
  - When editing a draft (save_mode=snapshot): primary CTA should communicate
    “new draft version” (e.g. “Spara ny utkastversion”).
  - When viewing a non-draft (save_mode=create_draft): primary CTA should
    communicate “create draft” (e.g. “Skapa nytt utkast”).
- Follow-up UX: Focus mode (collapse left sidebar) is tracked separately in
  ST-14-31 and is planned immediately after this story.
