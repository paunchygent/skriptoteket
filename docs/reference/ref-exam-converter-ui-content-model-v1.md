---
type: reference
id: REF-exam-converter-ui-content-model-v1
title: "Exam Converter UI content model v1"
status: active
owners: "agents"
created: 2026-05-14
topic: "exam-converter-ui-content"
links:
  [
    "EPIC-21",
    "ST-21-03",
    "PR-0325",
    "MOCK-st-21-03-exam-converter-authenticated-progressive-review",
    "045-huleedu-design-system",
    "REF-klassrumskartan-workspace-ui-doctrine-2026-03-28",
  ]
---

# Exam Converter UI Content Model V1

## Purpose

This reference defines the teacher-facing content model for Exam Converter
before any further UI layout or implementation work. It separates product UX
content from service contracts so upstream job fields do not leak into the
screen as duplicated, flat, or technical copy.

Exam Converter is a dense teacher workflow, not a status dashboard. The default
screen must help the teacher answer:

- what happened?
- what can I do next?
- which questions need my attention?
- which finished files can I download or save?

The model must be source-aware. The current authenticated proof slice starts
with DigiExam `.dxe`, but the same app must be able to present richer imported
question information from future QTI, Word, and PDF inputs without redesigning
the inspection surface.

## Content Boundary

User-facing Swedish copy must not expose service nouns, internal contract names,
or implementation state. These words are forbidden in visible UI copy unless the
user explicitly asks for technical details:

- `artefakt`
- `manifest`
- `bundle`
- `lease`
- `grant`
- `runtime`
- `pipeline`
- `Vault`
- `inloggad konvertering`

Service fields may still exist in TypeScript contracts, API clients, logs, and
tests. UI components must translate them into teacher actions and visible
outcomes.

## Primary Screen Regions

The authenticated Exam Converter screen has four content regions.

| Region | Default visibility | Purpose | Content |
|---|---:|---|---|
| Left workflow rail | Always visible | Collect inputs and start work | source upload, optional supporting files, target file choices, start/reset actions |
| Result strip | Visible after activity starts | State what happened and the next action | one status headline, one concise next-step line, report action when relevant |
| Inspection surface | One active mode at a time | Let the teacher inspect files, questions, or report details without flattening everything | segmented modes or equivalent disclosure: `Filer`, `Frågor`, `Rapport`; only the active mode renders its list/detail surface |

Do not add summary cards for item types, students, vanity metrics, or aggregate
status. Counts may appear in section headings only when they help navigation,
for example `Konverterade frågor (40)`.

## Progressive Disclosure

The default screen must not lay out all details flat.

1. Show one result headline and one next-step line.
2. Show one compact primary action row for the next likely action.
3. Let the teacher choose one inspection mode, for example `Filer`, `Frågor`,
   or `Rapport`.
4. Render only the active inspection mode. Do not show file rows, question rows,
   and report details at the same time.
5. In the question mode, show questions as a collapsed list with only scanning
   fields.
6. Expand exactly one question row or open one detail drawer when the teacher
   asks for details.
7. Put technical identifiers, source references, detected alternatives, warnings,
   and repair instructions inside the expanded row or detail drawer.

If the service only returns file-level data in the current slice, the UI must
show the file list and an empty question-list state. It must not invent question
counts, question types, points, detected answers, or manual review reasons.

The following composition is explicitly disallowed: result strip, full files
list, full question list, and multiple expanded question details all visible in
one default view. That is not progressive disclosure.

## Result Headlines

Use these exact headline states:

| State | Headline |
|---|---|
| Idle | `Välj provfil för att börja` |
| Running | `Konverterar provet...` |
| Complete | `Provet är konverterat` |
| Partial | `Konverteringen av provet lyckades delvis` |
| Failed | `Konverteringen av provet misslyckades` |

Next-step copy must be action-level and direct. Good examples:

- `Hämta filerna och kontrollera provet innan du använder det.`
- `Hämta rapporten och kontrollera frågorna som behöver ses över.`
- `Försök igen med en ny provfil eller välj färre målformat.`

Avoid vague states such as `Konverteringen behöver kontrolleras` or
`Provet är delvis klart`.

## Left Workflow Rail Content

The workflow rail is an ordered action rail, not an explanatory card stack.

1. `Ladda upp provfil (.dxe)`
   - uploaded state: `Filen är uppladdad`
   - empty state: `Välj provfil`
2. `Valfri: Resultat-PDF (för svarsmall)`
   - uploaded state: `Filen är uppladdad`
   - empty state: `Välj fil`
3. `Välj målfiler`
   - visible label: `PDF`
   - tooltip or inline explanation: `För direktimport av prov i Exam.net.`
   - visible label: `QTI-format`
   - tooltip or inline explanation:
     `För lagring och import av digitala prov. OBS! QTI-import är en planerad funktion i Exam.net och saknar stöd i nuläget.`
4. `Konvertera`
   - primary action: `Starta konvertering`
   - secondary action: `Rensa val`

Do not include broad instructional paragraphs by default. A short help disclosure
may exist, but it must stay collapsed unless the teacher opens it.

The current PR-0325 runtime may still label the required source upload as
`Ladda upp provfil (.dxe)`. Future source formats must reuse the same workflow
rail pattern with source-specific upload labels rather than creating a separate
application surface.

The workflow rail target-format step is a preview/declaration of intended
output formats, not the final save or download decision. The teacher should
review and complete question data first. Final download/save actions belong in
the `Filer` inspection mode after review, so generated target files are as
complete as possible.

## Files List Content

The files list uses compact rows. Each row may show:

- filename
- file kind, for example `PDF` or `QTI`
- size when known
- `Hämta`
- `Spara i mina filer`
- row disclosure for details

If a file cannot be created, the row copy should state the visible outcome and
the next action, for example `Kunde inte skapa QTI-paketet. Öppna rapporten och
kontrollera frågorna som behöver ses över.`

The files list belongs inside the active `Filer` inspection mode. It must not
remain as a large persistent panel while the teacher is reviewing questions.

## Question List Content

The question list is the main inspection surface once question data exists.
It must be a list or table of all converted questions, not a set of summary
cards.

The question list belongs inside the active `Frågor` inspection mode. The table
is a scanning surface; detailed correction happens in one selected row, one
side drawer, or one focused detail pane at a time.

Collapsed rows may show:

- question number
- short title or stem preview
- question type
- points
- dynamic imported-content indicators
- conversion status
- created files
- disclosure control

Dynamic imported-content indicators make the list useful across source formats.
They should show only safe, contract-backed facts that help the teacher see what
was imported, for example:

- `Facit importerat`
- `Svarsalternativ importerade`
- `Bedömningsanvisning finns`
- `Poäng importerade`
- `Endast frågetext`
- `Behöver kompletteras`

These indicators must be data-driven per question and source format. They must
not invent answer keys, points, alternatives, or grading notes when the
conversion contract does not provide them.

Expanded row or drawer may show:

- source question id from Sir Convert
- full stem when available
- detected alternatives or detected answer only when the contract marks it safe
- warning text translated into teacher action
- next action, for example `Kontrollera vilket alternativ som är rätt och markera korrekt svar.`
- optional deep link to the source question in Sir Convert when a governed link
  exists

Expanded rows must also support direct, low-friction completion in the
interface. When a question is incomplete or partially imported, the teacher
should be able to correct or add the missing safe fields directly where they are
reviewing the question, for example:

- mark or change the correct answer when alternatives are present;
- add or adjust points;
- confirm that a free-text answer has no machine-readable facit;
- mark a question as checked;
- keep a question excluded from a target file when the target cannot represent
  it.

These edits must be designed as question-level review actions, not as a detour
through a technical report. The goal is that the next PDF or QTI export is as
complete as possible with minimal unnecessary clicks.

Status labels:

- `Klar`
- `Behöver ses över`
- `Kunde inte konverteras`
- `Inte vald`

## Design Application

Exam Converter must use Skriptoteket tokens and Klassrumskartan dense-workspace
patterns:

- canvas and panel surfaces from `bg-canvas`, `bg-panel`, and
  `bg-panel-muted`;
- structure and long text from `text-navy` and `border-navy`;
- primary actions from `bg-action` / `text-button-primary-text`;
- warnings from `warning`, failures from `error` or `critical`;
- symbols and icons should use semantic token colors, not colorless neutral
  treatments by default: `action`/verdigris for interactive affordances, warm
  terracotta only as a small brand/accent signal, `success` for confirmed
  complete states, and `error`/`critical` for failed or destructive states;
- hard 4px corners and hard token shadows only where the workspace pattern calls
  for them;
- no Tailwind default palette leakage, gradients, decorative blobs, or large
  stacked cards.

The intended composition must be mocked and reviewed before further UI
implementation. The mockup must reflect this content model and the
Klassrumskartan workspace doctrine; it is not allowed to introduce new summary
cards, duplicated status blocks, or service jargon.

The selected mockup direction is retained in
`docs/mockups/st-21-03-exam-converter-authenticated-progressive-review/README.md`.
Its bottom stretched `Visa filer` reminder panel is explicitly rejected and
must not be implemented; file availability should instead live in the `Filer`
inspection mode or as compact header/mode metadata.

## UI Slice Approval Protocol

Every Exam Converter UI area must be treated as its own approved slice before
implementation. Do not implement a UI area directly from this reference or from
the selected whole-screen mockup.

For each UI slice, first send a proposal to the product owner that includes:

- the slice name and exact scope;
- a small mockup or focused visual sketch for that slice;
- the expected behavior and state transitions;
- the UI components and affordances to use, for example segmented control,
  dense icon button, disclosure row, detail pane, inline field, checkbox, or
  tooltip;
- why those component and affordance choices are recommended for this workflow;
- how the slice carries over Skriptoteket tokens, Klassrumskartan workspace
  invariants, and the progressive-discovery model;
- what is explicitly out of scope for the slice;
- the test-code shape that will describe and verify the slice behavior;
- any clarifying questions that must be answered before implementation.

Implementation may start only after the product owner explicitly approves that
slice proposal. Approval of one slice does not imply approval of adjacent UI
slices.

Recommended UI slice order:

1. app shell and authenticated Exam Converter host frame;
2. left workflow rail;
3. result strip and next-action copy;
4. inspection mode control;
5. question list scanning surface;
6. selected-question detail pane and completion actions;
7. files inspection mode;
8. report inspection mode;
9. empty, loading, failed, and partial states across the approved surfaces.

Service/runtime wiring is a separate implementation concern and must not be
used as a reason to skip UI slice approval.

## UI Slice Test-Code Contract

Every approved UI slice must have test code that reads as an executable
behavior specification for that slice. Tests are not allowed to be only
low-level selectors or snapshot assertions without explaining the user-facing
behavior they protect.

Each slice test module must include:

- a module header that states the slice purpose, the expected behavior, and the
  recommended implementation shape;
- `describe` and `it` text written around teacher-visible behavior, not
  implementation trivia;
- assertions for the primary state, at least one important alternate state, and
  the progressive-disclosure boundary for the slice;
- assertions that disallowed visible copy, duplicated panels, or service jargon
  do not appear when that slice controls the surface;
- the chosen component/affordance shape, either through the module header or
  narrowly scoped helper names.

Recommended test module header shape:

```ts
/**
 * Exam Converter <slice name> behavior.
 *
 * Slice purpose:
 *   Explain what this UI slice lets the teacher do.
 *
 * Expected behavior:
 *   List the visible states, state transitions, and progressive-disclosure
 *   boundary this test module protects.
 *
 * Recommended implementation shape:
 *   Name the component/affordance choices, for example workflow rail,
 *   segmented inspection modes, dense table rows, focused detail pane,
 *   tooltip, inline field, or checkbox.
 */
```

Do not turn tests into long design essays. The header should be short but
specific enough that a future maintainer can see why the slice has its current
shape before reading the component code.

## Implementation Gate

Before changing Exam Converter UI code again:

1. update or confirm this content model;
2. propose the next focused UI slice with its own mockup, behavior description,
   affordance/component choices, recommendation rationale, and clarifying
   questions;
3. get explicit product-owner approval for that slice;
4. write or update the focused test-code specification for that slice;
5. then implement only the approved slice.

Backend save/runtime work remains separate. UI copy and layout must never drive
service contract changes.
