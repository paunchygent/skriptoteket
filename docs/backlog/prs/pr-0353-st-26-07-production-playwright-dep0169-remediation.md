---
type: pr
id: PR-0353
title: "ST-26-07 Production Playwright DEP0169 remediation"
status: ready
owners: "agents"
created: 2026-06-14
updated: 2026-06-14
stories:
  - "ST-26-07"
tags:
  - devops
  - docker
  - playwright
  - renderer
  - klassrumskartan
  - security
dependencies:
  - "PR-0277"
  - "PR-0279"
acceptance_criteria:
  - "Given the production image installs the browser runtime, when the BuildKit production target is built with Node deprecation tracing enabled, then the build log contains zero `[DEP0169]` warnings."
  - "Given Klassrumskartan share-preview thumbnails still require browser rendering, when the production image is smoke-tested, then the Playwright-backed renderer produces a 1200x630 PNG from stored share HTML/CSS."
  - "Given Playwright is upgraded or its install shape changes, when dependency and browser binaries are inspected, then the checked-in lockfile, Dockerfile command, and `/ms-playwright` runtime path remain coherent."
  - "Given the remediation is reviewed, when `PR-0353` is closed, then retained evidence distinguishes app-code URL handling from Playwright build-time downloader warnings."
  - "Given the warning cannot be removed by a supported Playwright upgrade, when the task continues, then it moves browser rendering behind an explicit renderer-image/service boundary instead of suppressing Node warnings or downgrading Node only to hide them."
---

# PR-0353: ST-26-07 Production Playwright DEP0169 Remediation

## Problem

Hemma production Docker builds emit repeated Node `[DEP0169]` warnings during
the production image step that installs Playwright's Chromium runtime:

```dockerfile
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    pdm run playwright install --with-deps chromium
```

The warnings appear while Playwright downloads Chrome for Testing, FFmpeg, and
Chrome Headless Shell. They are not caused by Skriptoteket application URL
parsing, PR-0351 UI code, Conversion Hub/Sir Convert proof code, or the seating
export readiness smoke.

The local runtime evidence is:

- `Dockerfile` installs Playwright browsers in the `production` target.
- `pyproject.toml` keeps `playwright` in the runtime dependency set.
- `pdm.lock` currently resolves Playwright Python to `1.58.0`.
- Playwright Python `1.58.0` vendors Node `v24.13.0`.
- The vendored Playwright downloader calls `getProxyForUrl()` for each browser
  archive request.
- The Playwright `1.58.0` bundled proxy helper uses
  `require("url").parse`.
- Node 24 treats `url.parse()` as `DEP0169`: an application deprecation because
  the parser is not standardized and can have security implications. Node's
  official guidance is to use the WHATWG `URL` API instead; Node also states
  that CVEs are not issued for `url.parse()` itself.

This is lower immediate risk than an app request-path vulnerability because it
fires in a controlled build-time browser download path. It is still a real
production-image hygiene problem: the build emits security-relevant warnings,
the warning signal can hide later build regressions, and the browser runtime is
coupled to the main production image without a fresh review after the Playwright
toolchain moved forward.

## Solution

Remediate the warning without breaking the `ST-26-07` share-preview contract.
The supported solution is:

1. Upgrade Playwright Python from `1.58.0` to the current stable release
   available at implementation time (`1.60.0` as of 2026-06-14), regenerate
   `pdm.lock`, and rerun Playwright's browser install flow.
2. Build the production target with BuildKit and Node deprecation tracing to
   prove the exact `[DEP0169]` warning is gone, rather than relying on local
   macOS package inspection.
3. Keep the browser runtime only where the production thumbnail renderer needs
   it. Evaluate `playwright install --with-deps --only-shell chromium` because
   the renderer launches headless Chromium; adopt it only if the production
   container smoke proves the thumbnail renderer still works.
4. Replace any ad hoc `python -c` container smoke with a repo-owned script or
   existing command that renders one share-preview PNG and reports dimensions,
   byte size, and exit status without printing share contents.
5. If the supported Playwright upgrade path still emits `DEP0169`, do not hide
   the warning by downgrading Node or muting process warnings. Move
   Playwright/Chromium into an explicit renderer image or service boundary, and
   keep the main web image free of the warning-producing browser installer.

This keeps the product behavior intact: Klassrumskartan share pages still emit
renderer-derived Teams/social thumbnails, and the opened share URL remains the
canonical HTML/CSS artifact.

## Non-goals

- No removal of `ST-26-07` share-preview thumbnails.
- No change to the public-by-token share artifact model.
- No broad frontend, Conversion Hub, Sir Convert, auth, or seating export
  changes.
- No plain `docker build`; all production-image proof uses BuildKit.
- No hand-patching tracked files on Hemma.
- No suppression-only fix such as `NODE_NO_WARNINGS=1`.

## Implementation Plan

1. Use the testing skill before adding or editing tests.
2. Reproduce and capture the current warning with a traced BuildKit production
   build, retaining only sanitized log excerpts that show the stack owner.
3. Research the implementation-time Playwright Python release and official
   browser-install docs. Confirm whether the latest bundled proxy helper no
   longer calls Node's legacy parser on browser download URLs.
4. Update `pyproject.toml` and `pdm.lock` to the selected Playwright release.
5. Run `pdm run playwright install --dry-run --with-deps chromium` and record
   which browser archives the new release expects.
6. Build the production image with BuildKit and `NODE_OPTIONS=--trace-deprecation`
   so the build fails review if `[DEP0169]` still appears.
7. Add a narrow Dockerfile build arg, for example
   `PLAYWRIGHT_INSTALL_NODE_OPTIONS`, that is applied only to the Playwright
   browser-install `RUN` step. This lets the implementation prove downloader
   stack ownership with `--trace-deprecation` without making Node tracing a
   permanent production runtime setting.
8. Add or update a repo-owned production-container smoke command for
   `PlaywrightClassroomPlannerSharePreviewRenderer`; do not use inline
   multi-statement `python -c`.
9. Evaluate `--only-shell chromium` in the Dockerfile only after the container
   smoke proves the renderer works with headless shell alone.
10. Update `PR-0353`, `ST-26-07`, `EPIC-26`, and `.codex/handoff.md` with exact
   verification evidence before moving this task to `done`.
11. If the warning survives the supported upgrade, pause the dependency-only
    path and create the renderer-boundary change in this same PR slice or an
    immediately linked follow-up before closing the task.

## Test Plan

Focused code and dependency verification:

```bash
pdm run test tests/unit/application/apps/classroom_planner/test_share_artifacts.py tests/unit/web/apps/classroom_planner/test_share_pages.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_share_renderer.py
pdm run lint
pdm run typecheck
```

Production-image proof:

```bash
docker buildx build --build-arg PLAYWRIGHT_INSTALL_NODE_OPTIONS=--trace-deprecation --progress=plain --target production --load -t skriptoteket-pr0353-playwright-dep0169 .
docker run --rm --env PYTHONPATH=/app/src skriptoteket-pr0353-playwright-dep0169 pdm run <repo-owned-share-preview-smoke>
```

The BuildKit log must show no `[DEP0169]` lines. The container smoke must prove
one generated PNG has `width=1200`, `height=630`, nonzero bytes, and no
Playwright launch failure.

Docs and hygiene:

```bash
pdm run docs-validate
pdm run handoff-validate
git diff --check
```

## Rollback Plan

If the Playwright upgrade or Dockerfile install shape breaks thumbnail
generation, revert the dependency and Dockerfile changes while keeping the
captured evidence in `PR-0353`. Leave the task open or blocked; do not mark it
done with warnings suppressed, thumbnail generation disabled, or browser
runtime silently removed from production.
