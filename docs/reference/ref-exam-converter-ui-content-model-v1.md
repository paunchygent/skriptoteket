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
- `Öppna frågorna som saknar facit eller poäng.`
- `Försök igen med en ny provfil eller välj färre målformat.`

Avoid vague states such as `Konverteringen behöver kontrolleras` or
`Provet är delvis klart`.

Primary actions must use short button labels plus approved lucide symbols.
Do not put full explanatory sentences in button copy. The explanation belongs
in a dynamic help/info affordance, tooltip, or compact disclosure that appears
only when the teacher asks for it or focuses the action.

When a converted exam has actual missing `Facit` or `Poäng`, the teacher must
be able to choose between reviewing the questions and creating files from the
question data currently shown. The end-state action copy is:

- button: `Granska`; help/info copy:
  `Granska frågorna som saknar facit eller poäng.`
- button: `Skapa filer`; help/info copy:
  `Skapar filer med befintliga och godkända facit. Ogranskade AI-förslag används inte.`

`Skapa filer` submits the accepted-current-state export path. It is not a
local-only toggle and it is not AI-facit acceptance. It creates files from the
questions being shown plus any already accepted facit, and unreviewed AI-facit
suggestions must not be used. Starting a new conversion or clearing the selected
files must clear that acceptance.

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

The files list uses compact rows. In slices where the conversion result still
requires teacher review, the files list is a readiness surface, not an export
action surface. It must not compete with `Frågor` as the next step.

Each row may show:

- filename
- file kind, for example `PDF` or `QTI`
- size when known
- readiness status
- row disclosure for details

Download and save actions belong in the `Filer` mode after the review-decision
gate is clear. Do not render a generic `Åtgärd` column, and do not mix review
actions, report-reading actions, and export/save actions in one column.

File actions are available when either:

- the projection has no actual missing `Facit`/`Poäng` and no blocking warning;
  or
- the teacher has submitted `Skapa filer` to create files from the
  question data currently shown.

`Skapa filer` is not only a local UI state. In the end-state workflow it
must submit a governed accepted-state export path without claiming missing data
has been fixed. If Sir Convert initially marks a requested file as blocked
because `Facit` or `Poäng` is missing, Skriptoteket must create a governed
accepted-state export job instead of merely enabling a stale blocked row. If a
file is blocked for another reason, the row must stay disabled and show the
visible outcome, for example `Kunde inte skapas`.

Missing `Facit` or `Poäng` should guide the teacher toward `Granska`, but it
must not force review when the teacher knowingly wants to export the current
conversion.

If a file cannot be created, the row copy should state the visible outcome and
the next action, for example `Kunde inte skapa QTI-paketet. Öppna rapporten och
kontrollera frågorna som saknar facit eller poäng.`

If a first-pass file exists before review is complete, the row must not imply
that it is the final recommended export. Use visible outcome copy such as:

- `Skapad, men kontrollera frågorna först`
- `Kan hämtas när frågorna har kontrollerats`
- `Kunde inte skapas`

Avoid internal staging language such as `beredskap`, `förhandsberedskap`,
`export readiness`, or explanations of why a file is not final. The teacher
needs to know what happened and what they can do next.

The files list belongs inside the active `Filer` inspection mode. It must not
remain as a large persistent panel while the teacher is reviewing questions.

## Question List Content

The question list is the main inspection surface once question data exists.
It must be a list or table of all converted questions, not a set of summary
cards.

The question list belongs inside the active `Frågor` inspection mode. The table
is a scanning surface; detailed correction happens in one selected row, one
side drawer, or one focused detail pane at a time.

For the current authenticated DigiExam lane, `Frågor` is populated from Sir
Convert's read-only `digiexam-ir.json` and `migration-manifest.json` artifacts.
Skriptoteket parses those artifacts into a teacher-facing projection and must
not mutate the IR, create local reviewed state, or invent review outcomes.

If contract-backed missing data (`Facit` or `Poäng`) or warnings exist,
`Frågor` is the default active inspection mode. `Filer` becomes the default
only when no question review is required. A free-text item with
`manual_marking_required` is normal in this read-only slice and must not be
counted as `saknar facit eller poäng`; it can surface later through
teacher-marking or item-editing affordances. A generic upstream `partial`
bundle state caused only by free-text manual marking must not make the
teacher-facing result strip say that the conversion only partly succeeded.

Collapsed rows may show:

- one `Fråga` cell containing question number plus real prompt preview, for
  example `1. Varför är stål hårdare...`
- question type
- points
- missing-information indicators
- conversion status

Do not split `Nr` and `Fråga` into separate columns when the title is generic.
The source item id, for example `item-001`, belongs in the selected-question
detail pane only.

Question type labels must use teacher-recognizable Swedish terms, not
English-derived contract labels or nonstandard Swedish shortcuts. For DigiExam
choice items, do not use `Enval`. Use:

- `Flerval: ett val` for one-correct-choice items;
- `Flerval: flera val` for multiple-response items;
- `Flerval: matchning` for matching items when the source contract explicitly
  identifies matching structure; and
- `Lucktext` for source-backed gap-fill items.

Matching is a supported source-neutral IR and target-export shape when the
source contract identifies matching structure. The UI must not treat matching
as an unsupported or unknown target limitation merely because a source-specific
adapter has not emitted that shape in a particular fixture.

Missing-information indicators make the list useful across source formats
without turning the happy path into visual noise. The UI should not render
success pills for expected facts such as imported facit or imported points. If a
row shows a point value and no missing-facit indicator, the teacher can assume
that the normal data is present.

Indicators should be sparse, actionable, and contract-backed. Because the
column header already says `Saknas`, cell labels must stay short:

- `Facit`
- `Poäng`

These indicators must be data-driven per question and source format. They must
not invent answer keys, points, alternatives, or grading notes when the
conversion contract does not provide them.

Do not create missing labels for every possible item property. For example,
`Svarsalternativ` must not be shown as missing unless the conversion contract
explicitly proves that alternatives were expected and absent. When the contract
only says the item needs manual follow-up, do not invent a generic missing-field
label. Let the status symbol mark the row for attention and put the specific
contract-backed explanation in the selected-question detail pane if the source
data supports it.

For this slice, `manual_answer_key_required` maps to `Facit`, missing
`maxScore` maps to `Poäng`, and `manual_marking_required` for `Fritext` does
not map to a missing field.

Expanded row or drawer may show:

- source question id from Sir Convert
- full stem when available
- detected alternatives for all source-backed choice questions
- detected answer only when the contract marks it safe
- warning text translated into teacher action
- missing fields in a `Saknas` section, using field labels such as `Facit` or
  `Poäng` rather than repeating `saknas` in each label
- optional deep link to the source question in Sir Convert when a governed link
  exists

Choice alternatives are not optional decoration. For `Flerval: ett val`,
`Flerval: flera val`, and `Flerval: matchning`, the selected-question detail
must show the source-backed alternatives/options needed for the teacher to
decide whether missing `Facit` can be accepted as-is or must be corrected.
When alternatives are present but no source-proven correct marker exists, the
problem is missing `Facit`, not missing alternatives. The UI must not hide
alternatives and then ask the teacher to accept the current state.

`Lucktext` must be presented as source-backed gap-fill/open-cloze structure
when the IR proves gap blanks, source prompt text/HTML, and any embedded
references. Single-gap and multi-gap gapped items are supported by the
intermediate IR and by the QTI/PDF export contract. QTI must preserve keyed
gapped semantics when source, reviewed, or teacher-provided keys exist. PDF may
render gapped items as free text, but the exported PDF must still include the
accepted gapped-item key values. The UI must not present gapped items as
unsupported target shapes, and it must not collapse an implementation adapter
gap into `saknar facit eller poäng` unless `Facit` or `Poäng` is genuinely
missing from the current effective exam.

Expanded rows should eventually support direct, low-friction completion in the
interface. That completion requires an explicit Sir Convert mutation and
rebuild contract. Until that contract exists, the Skriptoteket UI must remain a
read-only projection and must not offer local-only controls that imply persisted
review or re-export readiness.

The read-only detail pane must not explain internal implementation gaps to the
teacher. Avoid copy such as `när redigering stöds`, `mellanformat`,
`mutation`, or instructions to use another service because Skriptoteket cannot
yet save the correction. If the current slice has no teacher action, the pane
should simply show the question, what is present, and what is missing.

Future mutation-backed review may allow the teacher to:

- mark or change the correct answer when alternatives are present;
- add or adjust points;
- confirm that a free-text answer has no machine-readable facit;
- mark a question as checked;
- keep a question excluded from a target file when the target cannot represent
  it.

These edits must be designed as question-level review actions, not as a detour
through a technical report. The goal is that the next PDF or QTI export is as
complete as possible with minimal unnecessary clicks.

Status in dense question rows should use approved lucide success/warning
symbols with accessible labels, not repeated visible text. The scanning row
must let the `Saknas` column carry the actionable missing-field labels. Use
screen-reader labels only when needed, for example `Klar`, `Saknas`, `Kunde
inte konverteras`, or `Inte vald`.

## Report Content

The report mode is diagnostic support. It is not the primary workflow and must
not replace question-level review.

The current lightweight report can be projected from `migration-manifest.json`
when it includes warning counts, manual-follow-up counts, and answer-key
provenance summaries. It should explain what needs attention and point the
teacher back to `Frågor`.

Useful report copy patterns:

- `Det här behöver kontrolleras`
- `Frågor där facit saknas`
- `Frågor med varningar`
- `Kontrollera frågorna i Frågor innan du använder filerna.`

Do not expose raw provenance enum names. Translate them into teacher-facing
phrases, but keep dense labels short when a heading already carries the
meaning. For example, a diagnostic sentence may say `Facit saknas`, while a
`Saknas` table cell should only say `Facit`.

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
6. review decision gate: `Granska` / `Skapa filer` with dynamic help/info
   copy;
7. selected-question detail pane and completion actions;
8. files inspection mode with download/save actions gated by review decision;
9. report inspection mode;
10. empty, loading, failed, and partial states across the approved surfaces.

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

## Live UI Inspection Gate

Future Exam Converter layout or breakpoint changes must include live internal-
browser inspection evidence for the approved slice. The inspection lane must
use the normal HuleEdu browser-session ceremony and must not rely on temporary
query hooks, direct product-backend credential posts, browser-local state
injection, or unreviewed component mutation.

Upload-gated post-conversion states require the governed dev/test-only fixture
lane defined by `PR-0327`. Breakpoint proof must record whether the desktop
table or the reduced question navigator is active, whether the inspector is
visible, and whether the document has horizontal overflow. Do not claim live
internal-browser proof for states that cannot be reached in the internal
browser.

## Breakpoint Composition Contract

Exam Converter follows the Klassrumskartan workspace rule: responsiveness
within breakpoints, not one responsive layout stretched across all breakpoints.
Phone, tablet/narrow-laptop, and desktop are separate approved compositions.

- Phone (`max-width: 767px`): a dedicated reduced companion workflow. It must
  not render the table/detail or navigator/detail compositions. It should show
  one primary review surface at a time, with readable AI-facit actions and no
  horizontal document overflow.
- Tablet and narrow laptop (`768px-1199px`): a reduced navigator plus visible
  detail composition. It must not inherit phone-only bottom-sheet or one-screen
  routing patterns.
- Laptop and desktop (`min-width: 1200px`): the dense table plus
  selected-question detail composition. It must not be flattened into stacked
  phone cards.

Structural breakpoint changes must be owned by CSS or by explicit Vue
presentation branches selected by semantic layout state. JavaScript must not
measure viewport width to own persistent layout geometry. All branches must
reuse the same review projection, AI-facit decision state, reviewed-completion
overlay builder, and Sir Convert Gateway submit path.
