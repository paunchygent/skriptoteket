---
type: mockup
id: MOCK-pr-0383-document-converter-mockup-and-copy-approval
title: "PR-0383 Document Converter mockup and copy approval"
status: approved
owners: "agents"
created: 2026-06-25
updated: 2026-06-25
tags: ["PR-0383", "ST-37-04", "document-converter", "mockup", "copy"]
summary: "Image-first and then HTML/CSS mockup package for the route-visible Document Converter workspace."
canonical_preview: "round-1-selected-project-workbench-token-corrected.png"
submission_policy: "Image direction and HTML/CSS mockup are approved; Swedish copy v4 is locked before PR-0384 production Vue implementation."
winner_policy: "PR-0384 must implement this approved package without reintroducing hidden backend options as visible UI controls."
---

# PR-0383 Document Converter Mockup And Copy Approval

## Purpose

Explore and approve the route-visible Document Converter workspace before
`PR-0384` implements production Vue. The package starts from the approved
`PR-0382` backend/API contract and keeps HTML/CSS project preview as the
dominant first-use workflow.

## Required Sequence

1. Image-generated mockups.
2. Product-owner approval or iteration.
3. HTML/CSS mockup based on the approved image direction. Round 1 created in
   `html-css-mockup/index.html`.
4. Product-owner approval or iteration. Approved on 2026-06-25 after the
   small-screen and no-eyebrow remediations.
5. Separate copy sheet and word-by-word copy approval. Locked as Swedish copy
   v4 under `copy-approval/`.
6. Separate production implementation in `PR-0384`.

## Current Product Truth Ledger

| Capability | Mockup treatment |
|---|---|
| HTML/CSS project preview | Dominant default workflow. |
| Up to 10 HTML entries | May be shown as the project-entry cap. |
| Up to 10 CSS files | May be shown as support files, not primary documents. |
| Linked images by filename | May be represented as safe project assets. |
| Uploaded fonts | Not available in the first contract. |
| PDF controls | Paper size must use the backend-backed A3/A4/A5 contract; orientation and margins stay out of the default page. |
| Output mode | Backend may support separate PDFs, combined PDF, or both; visible UI exposes `Exportera som` with only `Enskilda PDF-filer` and `Kombinerad PDF`. |
| Temporary previews | May show discard/regenerate/download/save, but not raw paths. |
| Save to `Mina filer` | Explicit teacher action only. |
| General batch conversion | Secondary workspace lane from `PR-0381`. |
| Durable history | Out of scope; belongs to `PR-0385`. |
| Visual token contract | Navy belongs to structure and the selected selector rail; command buttons stay neutral with token highlights. |
| Outcome-first UI | Main-page controls express input and desired output; app-owned conversion choices stay automatic. |
| Visual hierarchy | No eyebrow or overline labels; hierarchy comes from layout, selected state, and necessary control labels. |

## Image Round 1

The first image round was generated on 2026-06-25 after the product owner
confirmed the route-visible scope: HTML/CSS project preview is the dominant
default, and general batch conversion is secondary.

### Candidate A: Project Workbench

Dense operational workspace with a left project/file rail, a central PDF
control panel, and a large right-side PDF preview. This is the recommended
direction because it maps most directly to repeated teacher work and the
`PR-0382` preview contract.

Product-owner response: Candidate A is the most aligned and least cluttered
direction. It is selected as the base geometry for constraint hardening before
HTML/CSS mockup work.

### Candidate A2: Project Workbench Contract-Hardened

Candidate A2 keeps the Project Workbench geometry and corrects the contract
mapping for the HTML/CSS preview workflow:

- output mode is `separate PDFs`, `combined PDF`, or `both`;
- batch conversion is secondary, not the default workspace;
- image assets are filename-only project assets;
- uploaded fonts, SVG images, template editing, and template marketplace
  controls are excluded;
- download, save, discard, and regenerate operate from the server-owned preview
  state.

A2 is superseded for visual-token fidelity. It preserved the correct backend
contract shape, but overused navy-filled command buttons and internal helper
copy. It remains retained only as iteration history.

### Candidate A3: Project Workbench Token-Corrected

Candidate A3 keeps the Project Workbench geometry and A2 contract constraints
while correcting the compact application token treatment:

- navy is retained for structure, text, borders, and the moving selected state
  in the selector rail;
- ordinary command buttons such as add, render, regenerate, download, save, and
  discard use neutral canvas/panel surfaces with borders and token highlights;
- destructive preview discard uses restrained critical text/border treatment,
  not a filled danger button;
- unsupported controls such as project save/open, metadata/notes tabs, uploaded
  fonts, SVG controls, template editing, and template marketplace behavior are
  excluded.

A3 was the canonical image direction for the HTML/CSS mockup pass. It is
retained because it balances necessary operator choices with application
responsibility: the teacher selects inputs and desired output, while the app
owns internal rendering and conversion decisions. The later Swedish copy v4
handoff supersedes the visible English placeholder labels from that mockup
pass.

### Candidate B: Conversion Ledger

Top upload/config strip, central project/preview ledger, and a right-side
preview drawer. This direction is strongest if the product should emphasize
batch comparison and artifact bookkeeping over direct document preview.

### Candidate C: Document Studio

More guided operational workspace with project, controls, preview, and save
stages. This direction is calmer for first-time use but risks becoming too
wizard-like for repeated teacher work.

## HTML/CSS Mockup Round 1

The first static HTML/CSS mockup is available at
[`html-css-mockup/index.html`](html-css-mockup/index.html). It translates the
approved A3 direction into a reviewable browser artifact without production Vue
route activation.

Round 1 deliberately narrows the default main page:

- the left rail owns mode selection and project contents;
- the center panel exposes project intake, template choice, output mode, and
  real paper-size outcome choices only;
- application-owned conversion choices stay out of the default page; the screen
  shows only preview readiness, not renderer settings;
- margins, orientation, print-CSS toggles, page-break switches, embedding
  choices, producer choices, paths, preview ids, artifact ids, durable history,
  and advanced settings are absent from the default page;
- command buttons use neutral bordered treatment; navy fill remains limited to
  the selected selector rail.
- the paper-size control must be A3/A4/A5 and must not fall back to a
  Letter-style placeholder set.
- eyebrow/overline labels are absent from the visual UI; obvious surfaces are
  not narrated with duplicate subheadings.

`PR-0387` adds the approved small-screen remediation on top of this round:

- phone width is a reduced companion port, not a full stacked desktop
  workbench;
- preview becomes the first surface on phone, with render/download/save/discard
  still reachable;
- project inventory and readiness collapse into compact summary surfaces rather
  than a full rail dump;
- the phone shell keeps only mode context, selected project summary, and
  outcome controls needed for the conversion task.

The HTML/CSS mockup is approved and Swedish copy v4 is locked. `PR-0384` can implement
the production route from this package.

## Copy Approval Package

The external copy review package starts here:

- `copy-approval/copy-expert-brief.md`: assignment, output format, guardrails,
  and source-of-truth rules for the outside copy expert.
- `copy-approval/visible-string-inventory.md`: copy ids, current placeholder
  strings, accessibility labels, and strings explicitly out of scope.
- `copy-approval/swedish-copy-v4.md`: locked Swedish copy sheet and frontend
  handoff decisions.
- `.codex/repomix_packages/repomix-pr-0383-document-converter-copy-approval.xml`:
  regenerated Repomix package with the locked copy sheet; 15 files, 37,124
  tokens, no suspicious files detected.

## Copy Guardrails

- Swedish copy v4 is locked for `PR-0384` implementation.
- Image mockups used minimal placeholder labels; production UI uses the
  locked copy sheet.
- The copy sheet must separate visible UI strings from product notes.
- User-facing copy must avoid implementation terms such as artifact ids,
  filesystem paths, TTL internals, producer names, route ids, and validation
  vocabulary.

## Visual Token Guardrails

- Treat selector rails and command buttons as different control families.
- The selected selector-rail item may carry the approved navy moving-selection
  treatment.
- Normal command buttons must not use navy-filled CTA styling. They should
  render as compact neutral bordered controls with token-driven hover, focus,
  and active feedback.
- Use Verdigris/action only for small highlights, focus affordances, selected
  inline controls, and calm confirmation marks unless the HTML/CSS mockup
  approval explicitly narrows that further.
- Use critical/burgundy only for destructive text or border accents, not broad
  filled surfaces.
- If `PR-0384` implementation discovers a conflict between this approved
  package and `.codex/rules/045-huleedu-design-system.md`, stop and reconcile
  the design-token contract before production route work.

## Symbol Guardrails

- Use the canonical shared icon wrapper registry before adding a Lucide symbol.
- Existing wrappers cover ordinary controls such as file text, code, add,
  trash, download, vault/files, and zoom.
- Add Lucide-backed wrappers only when the canonical store lacks the semantic
  slot, such as image assets, PDF preview, refresh, page navigation, separate
  PDF output, or combined PDF output.
- Do not use hand-drawn SVG, CSS geometry, or one-off local icon shapes in
  production Document Converter controls.
- The static mockup uses official `lucide-static@0.563.0` mask assets pinned to
  the frontend Lucide version only to preview the approved symbol language.

## Outcome-First Guardrails

- Never make the teacher do the application's work.
- The main workspace should expose only the choices needed to supply input,
  choose the desired output, inspect the preview, download, save, or discard.
- The application owns rendering heuristics, safe asset handling, producer
  selection, default page decisions, and low-level conversion settings.
- Do not surface internal switches or broad option sets because they are easier
  than designing careful application logic.
- Advanced settings may become a separate future overlay only if a later slice
  proves a concrete teacher-facing need.

## Frontend Constraint Audit

The HTML/CSS mockup must preserve these build-facing constraints so `PR-0384`
can wire the approved layout to the existing backend without inventing new
contract behavior.

| Area | Constraint for the approved mockup |
|---|---|
| Primary mode | HTML/CSS project preview is the selected/default workspace. |
| Secondary mode | General batch conversion appears as a secondary lane or tab only. |
| HTML entries | Show project entries as first-class documents, capped at 10. |
| CSS files | Show CSS as support files, capped at 10, not as primary outputs. |
| Images | Show only filename-bound raster image assets within the project. |
| Fonts | Do not show uploaded fonts or font management. |
| Templates | Provide template selection only; no editing, marketplace, or saved templates. |
| PDF controls | Preserve backend-backed A3/A4/A5 paper-size choices; app-owned rendering decisions stay automatic or deferred. |
| Output mode | Preserve backend handling for `separate PDFs`, `combined PDF`, and `both`, but expose only `Enskilda PDF-filer` and `Kombinerad PDF` under `Exportera som` in the first UI. |
| Preview lifecycle | Preserve render/regenerate, download, save to `Mina filer`, and discard. |
| Temporary preview | Communicate temporary status without exposing TTL internals. |
| Authority | Never display raw filesystem paths, artifact ids, preview ids, or producer names. |
| History | Do not add durable history or previous-preview browsing. |

## HTML/CSS Mockup Requirements

- Keep the Project Workbench three-zone structure: project rail, controls, PDF
  preview.
- Keep the layout dense and operational; avoid landing-page composition,
  marketing cards, and explanatory hero copy.
- Use Skriptoteket app-shell conventions and local primitives where possible.
- Preserve the A3 token contract: neutral command buttons, navy selected rail,
  token highlights for hover/focus/confirmation.
- Preserve the outcome-first contract: the main page must not expose settings
  that merely compensate for missing application logic.
- Preserve real paper-size controls as A3/A4/A5, backed by
  `ConversionHubPdfPaperSizeV2`; do not reintroduce Letter.
- On phone width, use a reduced port: preview-first order, compact mode
  affordance, summarized project/readiness context, and no stacked desktop rail.
- Do not use eyebrow or overline labels in the app surface; keep only necessary
  control labels and structural headings.
- Use Swedish copy v4 from `copy-approval/swedish-copy-v4.md`.
- Do not render `dc.output.both`/`Båda` as a visible output segment.
- Use canonical icon wrappers first; add Lucide-backed wrappers only for
  missing Document Converter semantic slots.
- Replace image placeholder labels during the copy-review stage.

## Assets

- `round-1-candidate-a-project-workbench.png`: original Project Workbench
  direction.
- `round-1-candidate-b-conversion-ledger.png`: ledger-oriented alternative.
- `round-1-candidate-c-document-studio.png`: guided studio alternative.
- `round-1-selected-project-workbench-contract-hardened.png`: selected A2
  direction retained as superseded contract-hardening history.
- `round-1-selected-project-workbench-token-corrected.png`: canonical A3
  direction for HTML/CSS mockup work.
- `html-css-mockup/index.html`: static HTML/CSS mockup round 1.
- `html-css-mockup/styles.css`, `html-css-mockup/preview.css`, and
  `html-css-mockup/icons.css`: token-driven mockup styles and Lucide-backed
  symbol references.
- `copy-approval/copy-expert-brief.md`: outside copy expert assignment.
- `copy-approval/visible-string-inventory.md`: visible and accessibility
  string inventory.
- `copy-approval/swedish-copy-v4.md`: locked Swedish frontend handoff.

## Approval Log

- 2026-06-25: Product owner confirmed the first route-visible scope: HTML/CSS
  project preview is the dominant default and batch conversion is secondary.
- 2026-06-25: First image round generated with three directions: Project
  Workbench, Conversion Ledger, and Document Studio.
- 2026-06-25: Product owner selected Project Workbench as the most aligned and
  least cluttered direction. A contract-hardened A2 variant was generated to
  align output modes, asset rules, template limits, and preview actions with
  `PR-0382`.
- 2026-06-25: Product owner rejected the A2 visual-token treatment because
  navy-filled action buttons confuse selector-rail state with command buttons.
  A token-corrected A3 image now governs the HTML/CSS mockup pass.
- 2026-06-25: Product owner confirmed A3 as the preferred direction because it
  avoids unnecessary internal options and keeps the application responsible for
  conversion decisions beyond the teacher's desired input/output outcome.
- 2026-06-25: Static HTML/CSS mockup round 1 created from A3 with outcome-only
  main-page controls, preview-readiness status, and app-owned conversion
  decisions hidden from the default UI.
- 2026-06-25: Product owner requested removal of eyebrow/overline labels from
  the HTML/CSS mockup so obvious surfaces are not duplicated with subheadings.
- 2026-06-25: Product owner approved the remediated HTML/CSS mockup and
  approved preparing a Repomix-backed copy expert package before `PR-0384`.
- 2026-06-25: Product owner supplied Swedish copy v4 as the frontend handoff:
  visible output mode is narrowed to `Enskilda PDF-filer` and `Kombinerad PDF`
  under `Exportera som`; `Båda` must not render in the UI.
