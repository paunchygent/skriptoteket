---
type: pr
id: PR-0279
title: "ST-26-06 shared-link seating label typography and long-name fit"
status: in_progress
owners: "agents"
created: 2026-05-02
updated: 2026-05-03
stories:
  - "ST-26-06"
  - "ST-26-07"
tags: ["backend", "renderer", "css", "klassrumskartan", "sharing", "visual-proof"]
dependencies:
  - "PR-0276"
  - "PR-0277"
acceptance_criteria:
  - "Given a seating share page renders occupied seats, when two-line labels are shown in circular tokens, then the second line no longer obscures descenders or lower glyphs from the first line at desktop, mobile, and 1200x630 preview sizes."
  - "Given a seating share page contains ordinary long first names or surnames, when the renderer emits seat labels, then supported long names are defined by a deterministic weighted width budget and render in full through CSS-owned typography instead of defaulting to `...`."
  - "Given a seating share page contains names beyond the supported visual cap, when the renderer falls back, then the full label remains available through accessible/title text and the visible fallback is deterministic, documented, and visually contained."
  - "Given seating-only share CSS or label markup changes, when preview assets are generated, then seating renderer provenance advances while grouping renderer provenance and grouping CSS output remain unchanged unless explicitly governed."
  - "Given generated Teams/social preview thumbnails use the stored share artifact HTML/CSS, when long-name seating fixtures are rendered to 1200x630 PNG, then the full classroom map remains visible and no seat label overlaps adjacent rows or fixtures."
  - "Given visual proof runs, when supported full-name lines are present, then proof fails on hidden clipping via `scrollWidth > clientWidth`, empty visible lines, ellipsis styles, or literal `...` text."
  - "Given hostile or unusual display names are present, when share HTML/CSS and preview generation run, then escaping, no-script behavior, noindex metadata, and public-by-token boundaries remain covered by tests."
---

## Problem

The spatial seating share page now uses circular seat tokens, but the label
typography is too brittle for real classroom rosters:

- The two-line label stack is tight enough that the second line can visually
  obscure or clip the bottom of the first-line font.
- Ordinary long names fall back to `text-overflow: ellipsis`, which weakens the
  teacher-facing value of a seating map. Teachers should see full names within
  a reasonable visual cap, not a row of truncated labels.

The affected surface is the immutable shared-link seating renderer, not the
interactive Vue workspace. The same rendered share artifact also feeds
renderer-derived Teams/social preview PNGs, so the fix must treat page HTML,
CSS, and preview assets as one contract.

## Goal

Add deterministic long-name handling for shared-link seating labels while
preserving the static, CSS-owned renderer contract. The target is readable full
names for normal long-name cases, stable containment for extreme names, and no
vertical text collision inside circular seat tokens.

## Non-goals

- No share-token, slug, ownership, revocation, expiry, public-read, guest
  helper, or import/discovery semantics changes.
- No live draft sharing or owner-scoped API exposure.
- No SPA hydration, JavaScript text measurement, resize listeners, or runtime
  DOM calculations in the immutable share artifact.
- No broad redesign of classroom geometry, fixture semantics, or grouping
  share cards beyond what is necessary for seat-label containment.
- No replacement of full accessible labels with image-only or canvas-only text.
- No change to PDF renderer scope unless a shared print primitive already used
  by the share renderer needs a narrowly coordinated update.

## Implementation Plan

1. Inspect the current label path in
   `share_scene_renderer.py`: `_render_seat()`, `_student_name_lines()`, and
   `.room-seat__name-line`.
2. Define a small seat-label presentation helper that returns:
   - one or two visible lines
   - deterministic weighted-width tier classes such as compact, dense, and
     ultra-long
   - fallback state for over-budget name parts
3. Reuse or align with the existing print helper logic where practical, but do
   not couple share HTML to PDF output or broaden the renderer abstraction.
4. Fix vertical collision with CSS-owned geometry:
   - increase label line-height and/or token gap
   - keep the token centered
   - avoid clipping descenders
   - keep seat positions stable relative to benches and fixtures
5. Replace ordinary ellipsis behavior with tiered font handling:
   - no ellipsis for the weighted supported long-name range
   - smaller font size and tighter but readable line-height for long tiers
   - deterministic fallback only beyond the documented weighted cap
6. Keep fallback accessible:
   - preserve `aria-label` and `title` with the full escaped label
   - do not expose raw HTML or unescaped user-controlled text
7. Update renderer provenance and preview lifecycle:
   - keep grouping renderer provenance at
     `klassrumskartan-share-renderer-v1` when grouping output is unchanged
   - move seating renderer provenance to
     `klassrumskartan-seating-share-renderer-v2`
   - compose grouping and seating CSS separately so grouping artifacts do not
     include seating-only CSS
   - ensure stale seating preview assets are detected by
     renderer/source/presentation provenance
   - run or document `backfill-classroom-share-previews` for active seating
     links after deployment if existing preview rows would otherwise remain
     stale
8. Add focused renderer tests and visual proof using synthetic names that cover
   Swedish-style long first names, long surnames, double names, hyphenated names,
   width-budget boundary names, wide-token fallback, initials, and an extreme
   fallback case.

## Likely Code Entry Points

- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_scene_renderer.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_renderer.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/share_preview_renderer.py`
- `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/print_pdf_primitives.py`
- `src/skriptoteket/cli/commands/backfill_classroom_share_previews.py`
- `tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py`
- `tests/unit/application/apps/classroom_planner/test_share_artifacts.py`
- `tests/unit/web/apps/classroom_planner/test_share_pages.py`

## Test Plan

Required automated gates:

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/apps/classroom_planner/test_share_pages.py
pdm run lint
pdm run typecheck
pdm run docs-validate
git diff --check
```

Required visual proof:

- Generate a seating share HTML fixture with at least:
  - one ordinary short name
  - `KristofferJonatan`
  - `Alexanderthegreat`
  - one 18-character synthetic wide-token case
  - one long surname
  - one double or hyphenated name
  - one extreme fallback name
- Capture desktop, mobile, and 1200x630 preview PNGs using Playwright.
- Inspect or assert that:
  - first-line descenders are not obscured by the second line
  - supported long names render without `...`
  - every non-fallback visible label line has `scrollWidth <= clientWidth`
    within tolerance
  - visible label lines are non-empty unless intentionally absent
  - computed `text-overflow` is not `ellipsis`
  - extreme fallback remains contained and full text remains accessible
  - the classroom map still fits the preview image
  - no seat labels overlap neighboring rows, benches, fixtures, or the room edge
- Record artifact paths in `PR-0279`, `.codex/handoff.md`, and the retained
  review before closeout.

## Implementation Evidence

Current implementation changes:

- `share_scene_renderer.py` now emits deterministic seat-label fit classes for
  compact, dense, ultra-long, and fallback labels based on weighted width
  scores rather than raw character count.
- Shared seating label CSS now uses the seat token as the query container,
  increases line-height/gap to prevent first/second-line collision, and removes
  default `text-overflow: ellipsis` from seat labels.
- Ordinary supported long names render in full; extreme name parts fall back to
  initials while preserving the full escaped value in `aria-label` and `title`.
- `share_renderer.py` keeps grouping artifacts on
  `klassrumskartan-share-renderer-v1`, moves seating artifacts to
  `klassrumskartan-seating-share-renderer-v2`, and composes grouping/seating CSS
  separately so grouping previews are not invalidated by seating-only CSS.
- `scripts/prove_pr_0279_share_label_typography.py` creates the repeatable
  desktop, mobile, and 1200x630 preview proof, including scroll/client width
  clipping assertions and fallback `aria-label`/`title` checks.
- `compose.yaml` now keeps Docker web/worker Playwright execution on the
  Linux browser layer by setting `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` and
  clearing the host-only `PLAYWRIGHT_HOST_PLATFORM_OVERRIDE` inherited from
  `.env`; this prevents local Docker share creation from resolving macOS
  browser cache paths during preview PNG generation.

Latest proof run:

- Proof JSON:
  `.artifacts/pr-0279-share-label-typography/20260502T235526549245Z/proof.json`
- Static share HTML:
  `.artifacts/pr-0279-share-label-typography/20260502T235526549245Z/share-page.html`
- Desktop screenshot:
  `.artifacts/pr-0279-share-label-typography/20260502T235526549245Z/desktop.png`
- Mobile screenshot:
  `.artifacts/pr-0279-share-label-typography/20260502T235526549245Z/mobile.png`
- 1200x630 preview screenshot:
  `.artifacts/pr-0279-share-label-typography/20260502T235526549245Z/preview-1200x630.png`

The proof asserts occupied seat tokens across short, `KristofferJonatan`,
`Alexanderthegreat`, 18-wide-character fallback, long-surname, hyphenated, and
extreme-fallback cases. For desktop, mobile, and 1200x630 preview viewports,
all visible label lines were contained inside their seat tokens, first and
second lines were separated, `scrollWidth <= clientWidth` held within tolerance,
`textOverflow` computed to `clip` rather than `ellipsis`, no visible line was
empty, fallback cases preserved full `aria-label`/`title`, and no seat tokens
overlapped.

Verification run:

```bash
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py
PYTHONPATH=src:. pdm run python -m scripts.prove_pr_0279_share_label_typography
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/apps/classroom_planner/test_share_pages.py
pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/apps/classroom_planner/test_share_pages.py tests/unit/application/apps/classroom_planner/test_authenticated_shares.py tests/unit/application/apps/classroom_planner/test_public_shares.py tests/unit/web/apps/classroom_planner/test_share_api.py tests/unit/web/test_public_apps_classroom_planner_shares.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_pdf_renderer.py
pdm run handoff-validate
pdm run lint
pdm run typecheck
pdm run docs-validate
git diff --check
pdm run pytest -q tests/unit/test_docker_dev_shared_auth_contract.py
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 pdm run dev-stack build-start
docker exec skriptoteket_web pdm run python -c "<Playwright 1200x630 PNG smoke>"
docker exec -e PYTHONPATH=/app/src skriptoteket_web pdm run backfill-classroom-share-previews --fail-fast --limit 1
pdm run dev-stack ps
curl -sSf http://127.0.0.1:8000/healthz
```

The local Docker runtime follow-up was triggered by a live share creation
failure on `2026-05-02`: Playwright in `skriptoteket_web` resolved
`PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=mac-arm64` from `.env` and looked for
`chrome-headless-shell-mac-arm64` inside the Linux container. After the compose
fix and rebuild, the container exposes `/ms-playwright/chromium-1208` and
`/ms-playwright/chromium_headless_shell-1208`; the in-container smoke returned
PNG bytes and the app-owned backfill generated one preview with `failed=0`.

## Stop Conditions

Stop and ask before implementation if:

- Full-name rendering for ordinary long names would require JavaScript
  measurement inside the immutable share artifact.
- The fix would require changing share payload schemas or token/read lifecycle
  semantics.
- The visual cap cannot be defined without product input.
- Grouping preview invalidation remains accidental rather than explicitly
  governed.
- Proof cannot catch `overflow: hidden` clipping through DOM layout metrics.
- Seating preview asset staleness/backfill scope remains ambiguous after
  renderer changes.
- The implementation would exceed a narrow renderer/CSS correction and turn
  into a broader share-page redesign.

## Rollback Plan

Restore the previous share-scene label CSS and markup, then regenerate affected
preview assets if any were created with the new renderer version. No database
schema rollback should be required.
