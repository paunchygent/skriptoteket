---
type: pr
id: PR-0383
title: "ST-37-04 Document Converter mockup and copy approval package"
status: done
owners: "agents"
created: 2026-06-23
updated: 2026-06-25
stories:
  - "ST-37-04"
tags:
  - planning
  - frontend
  - mockup
  - copy
dependencies:
  - "PR-0380"
  - "PR-0381"
  - "PR-0382"
acceptance_criteria:
  - "Given the user requires a gated UI process, when this package starts, then it begins with image-generated mockups and iterates until the user approves the visual direction."
  - "Given production UI must not be invented directly, when image direction is approved, then a real HTML/CSS mockup is created and iterated until approved before production Vue work."
  - "Given copy must be user-reviewed word by word, when the mockup is approved, then a separate copy sheet is created and no copy is treated as final until explicitly approved."
  - "Given the app should match existing conversion-app conventions, when mockups are produced, then they adapt the current Skriptoteket/Vue design language rather than creating a new product style."
  - "Given compact curated-app controls distinguish selector state from command buttons, when the selected mockup is approved, then navy is limited to structure and selected selector-rail treatment while ordinary command buttons remain neutral with token highlights."
  - "Given the application must own implementation decisions, when the HTML/CSS mockup is produced, then the main page exposes only operator input/output choices needed to reach the desired outcome and keeps app-owned rendering decisions out of the default UI."
  - "Given dense curated-app hierarchy should avoid narrating obvious surfaces, when the HTML/CSS mockup is approved, then it uses no eyebrow or overline labels and keeps only necessary control labels or structural headings."
  - "Given the Swedish v4 copy handoff is approved, when PR-0384 implements the route-visible UI, then visible export choices render only `Enskilda PDF-filer` and `Kombinerad PDF` while any `both` backend value remains internal and unexposed."
  - "Given the shared symbol store governs icon semantics, when the mockup is approved, then controls use canonical wrappers first and only add Lucide-backed symbols for missing semantic slots."
---

# PR-0383: ST-37-04 Document Converter Mockup And Copy Approval Package

## Problem

Document Converter needs a route-visible app, but production UI and copy are
not allowed to be improvised. The product must move through the approved
mockup-first and copy-lock process before implementation.

## Goal

Produce the approved design and copy package for the Document Converter route
after backend contracts have stabilized enough to make the UI truthful.

## Blocked Until

- `PR-0381` proves the local/heavy producer and batch contract. Done and
  approved by `REV-PR-0381`.
- `PR-0382` defines the HTML/CSS project and preview contract. Done and
  approved by `REV-PR-0382`.
- The user confirms the route-visible scope for the first UI pass. Confirmed
  2026-06-25: HTML/CSS project preview is the dominant default, with general
  batch conversion secondary.

## Required Pipeline

1. Image-generated mockups.
2. User iteration until image direction is approved.
3. Real HTML/CSS mockup. Done.
4. User iteration until the HTML/CSS mockup is approved. Approved by product
   owner on 2026-06-25 after the no-eyebrow remediation.
5. Separate copy sheet using the user's copy-review protocol. Done: Swedish
   copy v4 locked by product owner on 2026-06-25.
6. Explicit user approval before `PR-0384` implementation. Done: the frontend
   handoff is ready for `PR-0384`.

## First Image Round

The first image-generation round starts from the approved `PR-0382` backend
contract and explores three route-visible workspace directions:

- Project Workbench: dense left project/file rail, central PDF controls, and a
  dominant right-side PDF preview.
- Conversion Ledger: top upload/config strip, central preview/job ledger, and a
  right-side PDF preview drawer.
- Document Studio: a more guided operational flow with project, controls,
  preview, and save stages.

Project Workbench was selected by the product owner as the most aligned and
least cluttered direction. A contract-hardened A2 image preserved the backend
mapping but was rejected for visual-token fidelity because it overused
navy-filled command buttons. The token-corrected A3 image governed the
HTML/CSS mockup pass: HTML/CSS project preview remains dominant, batch
conversion remains secondary, the selected selector rail may carry navy, and
ordinary command buttons remain neutral with token-driven highlight/focus
treatment. The final Swedish v4 frontend handoff narrows the visible output
mode control to `Enskilda PDF-filer` and `Kombinerad PDF`; backend `both` support is not exposed
as a user choice. A3 is preferred over the
earlier corrected image because it avoids surfacing internal implementation
details and keeps the teacher focused on input, desired output, preview, and
save/download actions.

The A3 image also keeps the mockup within the `PR-0382` contract by excluding
uploaded fonts, SVG assets, template editing, template marketplace behavior,
raw filesystem paths, artifact ids, and durable history.

The first HTML/CSS mockup round now exists at
`docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/index.html`.
It translates A3 into a static review artifact with outcome-only main-page
controls and no production route activation. `PR-0387` remediates the phone
breakpoint so it is a reduced curated-app port: preview comes first, project
inventory/readiness collapse into compact summary surfaces, and the full
desktop rail is not linearized on phone width. A follow-up product-owner pass
removes eyebrow/overline labels from the visual UI so hierarchy is carried by
layout, selected state, and necessary control labels instead of duplicated
subheadings. The product owner approved the HTML/CSS mockup on 2026-06-25.
The copy approval gate is also complete through the Swedish v4 frontend
handoff. `PR-0384` may now implement the route-visible production UI from this
approved package.

## Copy Approval Package

The copy approval pass used a focused Repomix package for outside copy review.
The product owner supplied, approved, and locked Swedish copy v4 for
implementation as the frontend handoff:
`docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/copy-approval/swedish-copy-v4.md`.

Copy is now locked for `PR-0384` implementation. The implementation must keep
strings in normal Swedish case, let components apply uppercase through CSS where
needed, and stop rather than changing visible strings without reopening copy
approval.

## Symbol Semantics Decision

`PR-0384` must use the canonical shared icon wrappers before adding any new
Lucide symbol. Existing wrappers cover file text, code, add, trash, download,
vault/files, and zoom controls. New Lucide-backed wrappers are allowed only for
Document Converter semantic slots the store lacks, including image assets,
preview, refresh, page navigation, separate PDF output, and combined PDF
output. Hand-drawn SVG, CSS geometry, and one-off local icon shapes are not
approved for production controls.

## Visual Token Decision

For this approval package, selector rails and command buttons are separate
families:

- selected rail state may use the approved moving navy selector treatment;
- normal actions such as add, render, regenerate, download, save, and discard
  must not use navy-filled CTA styling;
- command buttons should use compact neutral surfaces, navy borders/text, and
  token highlights for hover, focus, confirmation, or destructive accents.

If the HTML/CSS mockup or `PR-0384` implementation finds a conflict with
`.codex/rules/045-huleedu-design-system.md`, stop and reconcile the
design-token contract before building route-visible production UI.

## Outcome-First UI Decision

The default Document Converter page must not make the teacher do application
work. Controls on the main page must express the operator's input and desired
output, not implementation details that the application can infer or own.

- Main-page controls may cover project files, selected output family, preview,
  download, save, and only those PDF choices that directly describe the desired
  output.
- Visible output mode exposes only `Enskilda PDF-filer` and `Kombinerad PDF`. The backend may
  continue to accept `both` internally until a later contract change, but
  `both` must not render as a user-facing option.
- Paper size is a real output choice and must use the backend-backed
  A3/A4/A5 contract; Letter is not part of the first Document Converter
  project-preview main page.
- Rendering heuristics, safety decisions, asset handling, producer choices, and
  low-level conversion settings are application logic, not user work.
- Advanced settings are deferred to a future overlay or inspector if a later
  product slice proves they are truly needed.
- Do not approve UI complexity as a substitute for careful application logic.

## Non-goals

- No production Vue route or component changes.
- No backend contract changes.
- No generated API type changes.
- No copy changes beyond the locked Swedish v4 handoff.
- No remediation of the existing Audio Transcription route inside this PR;
  that drift is tracked separately.
- No advanced-settings overlay in this approval package.
- No new backend paper-size enum is needed unless a future check proves the
  existing A3/A4/A5 contract no longer renders correctly.

## Test Plan

- Focused backend contract tests if the mockup exposes backend-backed control
  values.
- Mockup index/docs validation if mockup docs are created.
- `pdm run lint` if tests or backend contract code changes.
- `pdm run typecheck` if tests or backend contract code changes.
- `pdm run docs-validate`
- `pdm run handoff-validate` if handoff changes
- `git diff --check`

## Verification Log

The table below combines package-wide proof gathered during `PR-0383`
iteration. `PR-0387` specifically reran screenshot proof, static audits,
`pdm run docs-validate`, and `git diff --check`; it did not require fresh
`lint`, `typecheck`, or `handoff-validate` runs because the remediation stayed
inside static mockup/docs surfaces and `.codex/handoff.md` was unchanged.

| Check | Result |
|---|---|
| HTML/CSS artifact file size audit | Passed: `index.html`, `styles.css`, `preview.css`, and `icons.css` are each under 500 lines; `.codex/handoff.md` is 199 lines. |
| Outcome-control audit | Passed: the HTML mockup exposes project inputs, output mode, A3/A4/A5 paper size, preview, download, save, and discard only; the phone view summarizes project inventory/readiness instead of dumping the full desktop rail; no default-page controls for producer, paths, ids, margins, orientation, print CSS, embedding, page breaks, advanced settings, or history. |
| Backend paper-size proof | Passed: `pdm run test tests/unit/application/curated_apps/test_document_converter_project_manifest.py tests/unit/infrastructure/documents/test_document_converter_project_previews.py` covered A3/A4/A5 manifest validation and WeasyPrint `@page size` CSS generation. |
| Visual token audit | Passed: `rg -n "#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\\b|rgba?\\(" docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/index.html docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/styles.css docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/preview.css docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/html-css-mockup/icons.css` returned no matches after the `var(--huleedu-paper)` preview-surface fix; the only navy-filled state remains the selected rail item and command buttons stay neutral with token highlights. |
| Symbol semantics audit | Passed: the static mockup now uses semantic `data-symbol` names, existing canonical wrapper names where available, and official `lucide-static@0.563.0` symbol masks for browser proof; no hand-drawn SVG or CSS geometry remains in the mockup icon layer. |
| Static rendering check | Passed: `pdm run playwright screenshot` captured desktop `1680x980` and full mobile `390x920` renders under `.artifacts/pr-0383-html-css-mockup-proof/`; desktop Project Workbench geometry remained intact and the phone render now uses a preview-first reduced port with summarized project context. |
| `PR-0387` focused closeout | Passed: regenerated `.artifacts/pr-0383-html-css-mockup-proof/desktop-1680x980.png` and `.artifacts/pr-0383-html-css-mockup-proof/mobile-390-full.png`; preserved red comparison screenshots as `desktop-1680x980-before-pr0387.png` and `mobile-390-full-before-pr0387.png`; reran static audits, `pdm run docs-validate`, and `git diff --check`. |
| Eyebrow-label audit | Passed: the static mockup removed the visual `.eyebrow` pattern, topbar label band, redundant section-label bands such as mode/project-content/desired-result/preview-readiness, and the mobile design-narration helper; refreshed proof is retained as `.artifacts/pr-0383-html-css-mockup-proof/desktop-1680x980-no-eyebrows.png` and `.artifacts/pr-0383-html-css-mockup-proof/mobile-390-full-no-eyebrows.png`; true form labels remain for accessible controls such as template, output mode, and paper size. |
| Copy expert package | Passed: `docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/copy-approval/copy-expert-brief.md`, `visible-string-inventory.md`, and `swedish-copy-v4.md` define the copy task, inventory, and locked handoff; Repomix generated `.codex/repomix_packages/repomix-pr-0383-document-converter-copy-approval.xml` with 15 files, 37,124 tokens, and no suspicious files detected. |
| Swedish copy v4 handoff | Passed: `docs/mockups/pr-0383-document-converter-mockup-and-copy-approval/copy-approval/swedish-copy-v4.md` records the locked Swedish copy sheet, hides `dc.output.both` from the visible UI, and updates the static mockup to `Exportera som` with two output segments: `Enskilda PDF-filer` and `Kombinerad PDF`; screenshot proof refreshed as `.artifacts/pr-0383-html-css-mockup-proof/desktop-1680x980-swedish-copy-v4.png` and `.artifacts/pr-0383-html-css-mockup-proof/mobile-390-full-swedish-copy-v4.png`. |
| `pdm run lint` | Passed 2026-06-25. |
| `pdm run typecheck` | Passed 2026-06-25. |
| `pdm run docs-validate` | Passed 2026-06-25. |
| `pdm run handoff-validate` | Passed 2026-06-25. |
| `git diff --check` | Passed 2026-06-25. |

## Stop Conditions

- Stop if asked to implement UI before image mockup approval.
- Stop if asked to lock copy before the separate copy sheet is reviewed.
- Stop if `PR-0384` reintroduces visible `Båda`/`both` as an output-mode
  segment without a new product-owner decision.
- Stop if the mockup tries to expose unresolved backend decisions as finished
  product behavior.
- Stop if the HTML/CSS mockup introduces controls not supported by `PR-0382`,
  including uploaded fonts, template editing, template marketplace behavior,
  visible artifact ids, visible preview ids, or durable history.
- Stop if the mockup or implementation normalizes navy-filled command buttons
  as a generic curated-app action style.
- Stop if the main page asks the user to choose settings that belong to
  application logic rather than the desired input/output outcome.

## Rollback Plan

Archive or remove the mockup package and copy sheet. Keep backend contracts and
previous planning docs unchanged.
