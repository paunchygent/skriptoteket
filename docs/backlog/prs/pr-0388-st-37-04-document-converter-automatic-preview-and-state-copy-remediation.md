---
type: pr
id: PR-0388
title: "ST-37-04 Document Converter automatic preview and state-copy remediation"
status: done
owners: "agents"
created: 2026-06-25
updated: 2026-06-26
stories:
  - "ST-37-04"
tags:
  - frontend
  - document-converter
  - remediation
  - preview
dependencies:
  - "PR-0384"
  - "PR-0387"
acceptance_criteria:
  - "Given the teacher has selected or added a supported HTML project file, when project inputs or output choices change, then the app automatically creates or refreshes the PDF preview without a persistent manual preview button."
  - "Given teachers may upload ordinary generated HTML, when the file is valid enough for the renderer to parse, then preview accepts it without imposing app-specific HTML structure, naming aesthetics, or required stylesheet-link patterns."
  - "Given uploaded HTML or CSS references an asset that is missing, undeclared, external, or outside the uploaded project boundary, when preview is generated, then the app renders a best-effort PDF with an in-document missing-asset indication instead of failing the whole preview."
  - "Given automatic preview can race with later edits, when an older render response returns after a newer request, then the UI ignores the older response and keeps the latest selected HTML/template/output/format state authoritative."
  - "Given project filenames may contain ordinary teacher-name separators, when an HTML filename produces an entry id with hyphens or underscores, then the backend accepts that entry id according to the project manifest contract and preview creation does not fail with validation."
  - "Given templates are currently internal renderer CSS presets, when the route renders the main page, then `Mall` is not exposed as a teacher-facing selector until the product has a visible, user-meaningful template contract."
  - "Given automatic refresh can fail after a previous successful preview, when the latest render fails, then the old PDF may remain visible only as recovery context, `Ladda ned` and `Spara i Mina filer` are disabled, and `Försök igen` is the only recovery action until the latest state renders successfully."
  - "Given file intake is project input, when the route renders on the main page, then adding files is a compact drop area that also opens the file picker on click, not a standalone CTA-styled button."
  - "Given preview creation fails, when the route shows `Det gick inte att skapa PDF:en.`, then retry is an icon-only circular retry control in the same feedback row as the error, not a detached text action dock."
  - "Given the main page must not expose implementation bookkeeping, when the route renders, then it has no readiness-status section pairing `Filer`, `Mall`, or `PDF` with `Klar`, no `Tillfällig förhandsvisning` eyebrow/status label, and no preview-artifact discard CTA posing as teacher work."
  - "Given preview means seeing the result, when a preview succeeds, then the route presents the generated PDF visually in the preview pane and enables `Ladda ned` and `Spara i Mina filer` for the selected server-owned artifact."
  - "Given preview must be a real workflow, when the implementation closes, then an authenticated live browser proof uploads a representative HTML/CSS/image project, waits for automatic preview creation, verifies the PDF is visually embedded, and proves download/save actions are enabled from the current artifact."
  - "Given copy should describe visible outcomes only, when preview generation is idle, loading, successful, stale, or failed, then the UI uses only necessary teacher-facing copy such as `Skapar PDF...`, `Det gick inte att skapa PDF:en.`, and a failure-only `Försök igen` action."
---

# PR-0388: ST-37-04 Document Converter Automatic Preview And State-Copy Remediation

## Problem

`PR-0384` shipped the first authenticated `/apps/document-converter` route, but
route use exposed a product mismatch: the page asks teachers to click a
manual `Förhandsvisa` action, presents hard-coded readiness rows, and labels the
result area with `Tillfällig förhandsvisning`. Those labels are implementation
bookkeeping, not teacher work.

The visible route also treats preview as an artifact/action state rather than a
true visual preview. Product language and behavior must converge: if the app
says preview, the teacher should see the generated PDF.

Manual local testing also exposed a contract bug that the first proof fixture
missed: teacher filenames such as `agnes-leandersson.html` produce hyphenated
HTML entry ids. The backend manifest contract says entry ids may contain
letters, numbers, hyphens, and underscores, but the current validator rejects
those separators and returns `422 VALIDATION_ERROR`.

This is accidental over-validation. The preview contract is not that teachers
must supply specially shaped HTML. The application may enforce only safety and
boundedness: supported file kind, file size/count limits, duplicate/bare
filename handling, project-boundary asset resolution, and renderer failure for
genuinely unreadable/broken input. Inline CSS and uploaded CSS files must both
be accepted; uploaded CSS support is additive project styling and must not
depend on the HTML explicitly linking every CSS file.

The asset contract is also best effort. Missing, undeclared, external, or
unsafe linked assets must not produce a generic failed preview when the
document can otherwise render. The renderer should block unsafe fetches, make
the missing resource visible in the generated PDF where practical, and continue
building the preview from the files the teacher did provide.

## Goal

Make preview application-owned. Adding/selecting a supported HTML file or
changing template, output mode, or paper format should automatically create the
current PDF preview from the selected HTML plus safely linked project CSS and
images. The user should only choose input and desired result; the application
owns rendering, refresh timing, stale-response handling, and artifact lifecycle.

## Product Decisions

- Remove the persistent `Förhandsvisa` button from the main page.
- Remove the readiness-status section that pairs `Filer`, `Mall`, or `PDF`
  with `Klar`; those rows are implementation readiness bookkeeping. The
  template field label `Mall` and ordinary `PDF` media/result copy remain
  allowed when they are part of truthful visible UI.
- Remove the visible `Mall` selector from the main page for this slice. The
  current backend `template_id` values are internal CSS presets applied during
  PDF rendering, not teacher-visible templates with enough visible affordance
  to justify a default-page choice.
- Use the internal default template value when submitting previews. A later
  visible template selector needs a separate approved contract with previews or
  otherwise user-meaningful distinctions.
- Remove `Tillfällig förhandsvisning`; it is a forbidden eyebrow/status label
  and does not help the teacher complete the workflow.
- Do not show an empty-state sentence such as `Ingen PDF ännu` when absence of
  a preview is already clear from the pane and disabled actions.
- Use `Skapar PDF...` only while the app is actively generating a preview.
- Use `Det gick inte att skapa PDF:en.` for failed preview generation, paired
  with a failure-only icon retry action in the same feedback row as the error.
- Do not render `Försök igen` as a detached text button or as a separate action
  dock. Its placement must make the recovery relationship visually obvious.
- Replace the standalone `Lägg till fil` button treatment with a compact file
  drop area. Clicking the drop area still opens the native file picker, and
  dropping files uses the same validation and merge behavior as picker input.
- Treat linked assets as best effort. If an asset reference is missing,
  undeclared, external, or outside the uploaded project boundary, do not fetch
  it and do not fail the whole preview when the remaining HTML can render.
  Show a visible missing-resource indication in the PDF where practical.
- Treat ordinary grid-heavy teacher HTML/CSS as in-scope generated input, not
  as a separate follow-up class. The runtime dependency must use WeasyPrint
  `>=69.0`, and the application must prove representative Grid output through
  the real renderer. Try native Grid rendering first; if WeasyPrint still hits
  an internal grid-layout failure, retry through an app-owned print
  compatibility fallback that preserves readable content instead of failing the
  whole preview. The scoped preview contract is best-effort teacher output, not
  pixel-perfect native Grid fidelity.
- Do not show success copy. The rendered PDF and enabled `Ladda ned` /
  `Spara i Mina filer` actions are the success state.
- If automatic refresh fails after a previous successful preview, keep the last
  PDF visible only as recovery context, disable `Ladda ned` and
  `Spara i Mina filer`, show the approved failure copy with `Försök igen`, and
  re-enable artifact actions only after the latest selected state renders
  successfully.
- Keep `Enskilda PDF-filer` and `Kombinerad PDF`; do not expose backend `both`.
- Keep preview artifacts server-owned. Do not expose raw paths, artifact ids,
  TTL language, or browser-supplied artifact authority.

## Non-goals

- No new backend storage model.
- No `Mina filer` source selection or durable history; that remains `PR-0385`.
- No template marketplace, visible template selector, advanced settings,
  margins, orientation controls, or renderer/debug controls.
- No public anonymous Document Converter lane.
- No route/app-presentation contract expansion through `PR-0369`.
- No new PDF rendering dependency unless the implementer first records current
  library research and a reason the browser-native PDF surface is insufficient.

## Implementation Plan

1. Update the route composable so preview generation is automatic and debounced
   after file selection, selected HTML changes, output-mode
   changes, and paper-format changes.
2. Add request sequencing or abort handling so stale render/download responses
   cannot overwrite newer selected state.
3. Fix the backend project manifest entry-id validator so hyphens and
   underscores are accepted according to the documented contract, with focused
   regression coverage for a hyphenated HTML filename. Do not replace this
   with stricter HTML-shape validation.
4. Change the project asset fetcher/renderer from fatal missing-resource
   behavior to best-effort blocked/missing-resource handling. Network,
   filesystem, path traversal, nested path, and undeclared project-resource
   references must remain sandboxed and must not be fetched.
5. Render the successful PDF artifact visually in the preview pane using a
   server-authorized artifact download and a local object URL, with cleanup when
   the selected preview changes or the component unmounts.
6. Remove the manual preview button, readiness block, preview-artifact discard
   action, and forbidden eyebrow/status label from the main page.
7. Track whether the visible preview artifact matches the latest selected
   HTML/output/format state. Keep download/save actions disabled until
   a current preview artifact exists.
8. Replace the file-picker button presentation with a compact drop area whose
   click and drag/drop paths share the same project-file validation.
9. Move retry into the feedback row as an icon-only circular control using the
   canonical icon store; only add Lucide if the canonical store lacks the symbol.
10. Add focused Vitest coverage for auto-preview, stale-response protection,
   failed-refresh recovery, structural forbidden-surface absence, failure retry,
   and PDF-object cleanup.

## Red-First Proof Plan

- Component red: after adding a valid HTML file, no automatic preview request is
  made today until the user clicks `Förhandsvisa`.
- Component red: current UI renders the readiness-status section that pairs
  `Filer`, `Mall`, and `PDF` with `Klar`, and renders the
  `Tillfällig förhandsvisning` eyebrow/status label.
- Component red: out-of-order preview responses can currently update shared
  preview state without a route-level latest-request guard.
- Component red: the preview pane does not embed the generated PDF artifact.
- Component red: after a successful preview, changing a governed setting and
  receiving a failed automatic refresh does not yet prove that the old artifact
  actions are disabled until the latest state renders successfully.
- Backend red: a valid project manifest with an HTML entry id derived from a
  hyphenated filename such as `agnes-leandersson.html` is rejected even though
  the contract permits hyphens and underscores.
- Backend/infrastructure red: HTML that references a missing, undeclared, or
  external asset currently fails preview generation instead of rendering the
  remaining document as a best-effort PDF with a visible missing-resource
  indication.
- Component red: the main route exposes `Mall` as a visible selector even
  though the current choices are internal renderer CSS presets without a
  user-meaningful route-visible template contract.
- Component red: file intake is styled and announced as a normal action button
  rather than a compact drop area with shared picker/drop behavior.
- Component red: `Försök igen` is rendered as a detached text action instead of
  an icon-only retry control in the error feedback row.

## Green Proof Plan

- Focused Vitest:
  `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
- Type/lint/build gates:
  `pdm run fe-type-check`
  `pdm run fe-lint`
  `pdm run fe-build`
- Browser-visible route proof through the authenticated shared-auth lane, with
  retained screenshots and machine-readable proof that:
  - logs in through the HuleEdu browser-session ceremony, not local cookie or
    credential shortcuts;
  - uploads a representative local sample project containing HTML, CSS, and at
    least one linked image resolved by filename within the project boundary;
  - uses at least one hyphenated HTML filename so backend entry-id validation is
    exercised by the same path teachers use locally;
  - exercises inline CSS, uploaded CSS, and a blocked or missing linked asset,
    proving the preview is best effort rather than all-or-nothing;
  - waits for automatic preview generation without clicking a preview button;
  - verifies the preview pane embeds the current PDF artifact visually;
  - verifies `Ladda ned` and `Spara i Mina filer` become enabled only after the
    current preview artifact exists;
  - verifies file intake is a compact drop area and retry is an icon-only
    control inside the error feedback row;
  - verifies a later output/format change triggers another automatic preview
    without a preview button;
  - verifies the main route does not expose the internal `Mall` selector;
  - verifies forbidden legacy surfaces are absent: the readiness-status section
    that pairs `Filer`, `Mall`, or `PDF` with `Klar`, the persistent
    `Förhandsvisa` button, and the `Tillfällig förhandsvisning` eyebrow/status
    label.
  Focused Vitest must cover the failed-refresh path: after a successful
  preview, changing a governed setting and receiving a failed automatic refresh
  keeps any old PDF visual disabled for artifact actions, shows
  `Det gick inte att skapa PDF:en.`, exposes only `Försök igen`, and re-enables
  download/save only after a successful render for the latest state.
- Docs/handoff gates:
  `pdm run docs-validate`
  `pdm run handoff-validate`
  `git diff --check`

## Implementation Proof

- Red-first backend proof initially failed under
  `pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py`
  because hyphenated/underscored entry ids were still rejected and missing or
  blocked linked assets still failed the whole preview path.
- Red-first frontend proof initially failed under
  `pdm run fe-test -- --run src/views/apps/document-converter/DocumentConverterView.spec.ts`
  because the route still exposed `Mall`, still rendered the standalone
  `Lägg till fil` and detached retry surfaces, and did not yet satisfy the
  compact drop-zone and inline icon-retry expectations.
- The implemented backend now accepts `agnes-leandersson` and `alma_winald`
  entry ids, keeps asset fetching sandboxed, returns a visible safe placeholder
  for blocked or missing image-like resources, degrades blocked CSS/font-like
  resources safely, and still fails only when no usable PDF can be rendered.
- The implemented frontend now keeps `academic_phd` internal, removes the
  visible `Mall` selector, shares picker and drag/drop validation through one
  intake path, preserves automatic preview sequencing/object-URL cleanup, and
  moves retry into the error row as an icon-only `Försök igen` control.
- Reviewer/user follow-up rejected simplifying the proof fixture away from
  ordinary grid-heavy teacher HTML/CSS. The repaired implementation keeps the
  representative fixture, tries native WeasyPrint Grid first, and falls back to
  app-owned print compatibility only when the renderer hits the known internal
  Grid `AssertionError`. That fallback is part of the approved best-effort
  preview contract, not a reason to remove support for the input.
- Retained review follow-up found two fallback defects before approval:
  fallback CSS replacement must not mutate visible body text, and unrelated
  renderer `AssertionError`s must not trigger the Grid retry. The repaired
  implementation now scopes CSS softening to `<style>`, `style=`, and linked
  CSS through an HTML parser, requires a WeasyPrint `layout/grid.py` traceback
  for Grid retry, and covers both risks with focused regression tests.
- The extracted helper `scripts/_document_converter_proof.py` keeps the
  oversized browser script under the repo cap while the fixture again uploads a
  hyphenated `agnes-leandersson.html`, linked `project:///styles.css`, inline
  CSS, a linked in-boundary image, hidden blocked probes, and a missing linked
  asset that together prove ordinary HTML/CSS best-effort rendering.
- Chromium's native blob-backed PDF iframe still is not trustworthy for DOM
  inspection, so the retained proof keeps the authenticated browser flow as the
  route proof and then downloads the current preview artifact, renders page 1
  to `document-converter-preview-desktop.page-1.png` and
  `document-converter-preview-compact.page-1.png`, and records machine-readable
  checks in `manifest.redacted.json` for expected heading/callout/caption text,
  visible CSS/image accent colors, visible missing-resource text, and absence
  of raw external URLs or file paths.
- Earlier repair attempts under
  `.artifacts/authenticated-home-work-apps/20260625T225535Z/`,
  `.artifacts/authenticated-home-work-apps/20260625T225726Z/`, and
  `.artifacts/authenticated-home-work-apps/20260625T225910Z/` retained
  `422 VALIDATION_ERROR` responses while the proof fixture was still using a
  grid-heavy layout that triggered WeasyPrint internal failure. Docker-backed
  inspection with
  `docker logs skriptoteket_web --since 2026-06-25T23:01:50Z --until 2026-06-25T23:02:40Z 2>&1 | rg 'project-previews|Document Converter project preview render failed|VALIDATION_ERROR|AssertionError'`
  isolated the remaining failure to a WeasyPrint `AssertionError` in grid
  layout during the proof fixture render, not to the repaired hyphenated
  entry-id validator.
- Focused backend verification for the repaired renderer passed:
  `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib /opt/homebrew/bin/pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py tests/unit/infrastructure/documents/test_document_converter_project_renderer_best_effort.py tests/unit/cli/test_cleanup_document_converter_project_previews.py`
  passed with `43 passed`, including representative Grid fixtures,
  best-effort missing/blocked asset rendering, linked-CSS compatibility retry
  coverage, traceback-scoped Grid retry, visible text preservation, and CLI
  cleanup import coverage.
- Fresh shared-auth proof after the BuildKit image rebuild and import repair
  produced `.artifacts/authenticated-home-work-apps/20260626T031626Z/` with real
  rendered PDF PNG evidence, linked CSS/image proof, missing-resource text, no
  raw path or external URL leakage, refreshed blob iframe source, and enabled
  download/save.
- The matching Docker log window records native WeasyPrint Grid
  `AssertionError`, then
  `Document Converter project preview retried with grid compatibility fallback.`,
  followed by preview POST/artifact GET `200` responses. That proves the scoped
  best-effort contract: Grid-heavy input does not collapse preview generation
  and the asset sandbox remains intact.

## Review Gate

`REV-PR-0388` approved this implementation package on 2026-06-26. The retained
review confirmed product truthfulness, stale-response safety, copy discipline,
artifact authority, and the repaired best-effort Grid fallback proof.

## Stop Conditions

- Stop if visual PDF preview cannot be implemented without raw filesystem
  paths, browser-supplied artifact authority, or direct Sir Convert calls from
  the browser.
- Stop if automatic preview needs backend contract changes outside the existing
  project-preview artifact endpoints.
- Stop if the UI needs new explanatory copy, empty-state prose, advanced
  controls, or implementation/status labels beyond this approved contract.
- Stop if a PDF rendering dependency becomes necessary and has not been
  researched against current documentation.
- Stop if this work tries to unblock or reopen `PR-0369` without a concrete
  app-presentation API contract need.

## Rollback Plan

Restore the `PR-0384` manual-preview route behavior while keeping backend
project-preview endpoints and existing Document Converter route activation
intact. Remove automatic preview timers, object URL handling, new tests, and
copy-remediation changes.
