---
type: task
id: TASK-SKRIPT-42-01-03
title: Klassrumskartan share pages render Ljust, Midnatt or Bläck from the stored choice and print light
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-11-01'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Share pages pick a Ljust, Midnatt or Bläck palette from the huleedu_theme cookie or, with no cookie, from prefers-color-scheme, show no theme button, and print light
story: ST-SKRIPT-42-01
backlog_document_profile: contract-derived
---

## Implementation Contract

Klassrumskartan share pages render in Ljust, Midnatt or Bläck. The page follows
the stored `huleedu_theme` choice, or the device when none is stored, has no
theme button, and prints light.

- Renderers:
  - `SHARE_BASE_CSS` keeps the Ljust variables on `:root`, so the PDF and the
    preview image stay light.
  - It adds `:root[data-theme="midnight"]` and `:root[data-theme="dark"]`
    palette blocks, plus
    `@media (prefers-color-scheme: dark){:root[data-theme="system"]{…Midnatt…}}`.
  - Under `@media print` it forces the Ljust values and `color-scheme: light`.
  - Midnatt has its own palette, distinct from Bläck.
  - Every colour literal in `share_scene_renderer.py` and
    `share_group_renderer.py` becomes a `var()` of those variables.
  - `share_preview_renderer.py` stays light.
- Versions: the grouping renderer goes from v1 to v2 and seating from v2 to
  v3. After deploy, the existing backfill CLI re-renders stored seating
  shares through `refresh_seating_share_artifact_if_needed`. Legacy grouping shares have no `presentation_payload`, so they keep
  their stored light page.
- Route: `read_classroom_planner_share`
  - reads the `huleedu_theme` cookie;
  - maps any value other than `light`, `dark`, `midnight` or `system` to
    `system`;
  - inserts `data-theme="<value>"` into the first `<html` tag of the stored
    HTML;
  - keeps `Cache-Control: no-store`.
- Non-goals: PDF, DOCX and XLSX exports, the preview image, and a theme button.

## Contract Inputs

- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/`:
  - `share_renderer.py`: `SHARE_BASE_CSS` at line 53, the print block at lines
    181-192, `_document` at line 276, and the renderer versions;
  - `share_scene_renderer.py`;
  - `share_group_renderer.py` (`#fff` at lines 34 and 79);
  - `share_preview_renderer.py`, which stays light.
- `src/skriptoteket/application/curated_apps/classroom_planner/share_artifact_refresh.py`:
  `refresh_seating_share_artifact_if_needed` re-renders a seating share whose
  `renderer_version` differs from the current version, using its stored
  `presentation_payload`.
- `src/skriptoteket/web/routes/classroom_planner_share_pages.py`:
  `read_classroom_planner_share` at line 157.
- `src/skriptoteket/cli/commands/backfill_classroom_share_previews.py`.
- Palette values: the Ljust, Midnatt and Bläck blocks of
  `src/skriptoteket/web/static/css/huleedu-design-tokens.css`.

## Core Vertical And Performance

Units, one junior each, with disjoint files:

1. U1, renderers: the palettes, the print block, the `var()` conversion, the
   version bump, and a unit test that parses `huleedu-design-tokens.css` and
   asserts each palette value equals its token.
2. U2, route: the cookie read, the value validation and the attribute
   insertion.

No performance concern: inserting the attribute is one string replace per
request.

## Validation

- U1: `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py`
  - asserts the three palettes equal the token values;
  - asserts the print block forces Ljust;
  - asserts the scene and group CSS hold no colour literal.
- U2: `tests/unit/web/apps/classroom_planner/test_share_pages.py`
  - a cookie of `dark`, `midnight`, `light` or `system` gives that
    `data-theme`;
  - a missing or invalid cookie gives `system`;
  - `Cache-Control` stays `no-store`.

## Stop Conditions

- A share variable has no matching token in one of the themes: stop and report
  it.
- Stored share HTML has no `<html` tag: report it, and do not change the
  stored data.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------------------------------- |
| S1  | Share pages follow the stored `huleedu_theme` choice, or the device when none is stored, and show no theme button.        |
| M3  | Share renderers emit a palette per theme (Ljust, Midnatt, Bläck), pick it from the cookie or the device, and print light. |
| M5  | Share pages give Midnatt its own palette, distinct from Bläck.                                                            |
| X7  | The palettes live in the stored CSS, keyed on `data-theme`; a unit test pins them to the token values.                    |
| X8  | The route validates the cookie and inserts `data-theme` into the first `<html` tag.                                       |
| X9  | Grouping goes to v2 and seating to v3; the backfill re-renders seating shares; legacy grouping shares stay light.         |
