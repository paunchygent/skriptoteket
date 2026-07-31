---
type: reference
id: REF-SKRIPT-GENERAL-exam-converter-ui-content-model-v1-PART-02
title: Exam Converter UI content model v1 — part 02
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-exam-converter-ui-content-model-v1
part: 2
---

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

### Design Application

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

The PR-0406 small-screen answer-key review decision is retained separately in
`docs/mockups/pr-0406-answer-key-review-small-screen/README.md`. That bundle is
exact decision material for the represented phone layout and copy: pending
AI suggestions use `Granska`/`Acceptera`, completed reviewed keys use `Klart`
without an AI badge, teacher-owned changes may use `Ändrat`, validation issues
use concrete missing-key language, and manual repair uses disabled/enabled
`Spara facit` semantics. Its represented symbols must follow the approved
symbol contract: `IconAi`/`Sparkles` for AI, `IconCheck`/`Check` for
reviewed/selected state, `IconEdit`/`PencilLine` for teacher-owned changed
state, and `IconWarning`/`AlertTriangle` for validation problems.

The PR-0406 desktop answer-key review alignment is retained in
`docs/mockups/pr-0406-answer-key-review-desktop/README.md`. The desktop
workbench keeps the left workflow rail, central question table, and one
selected-question detail pane for `Frågor`, while `Filer` and `Rapport` remain
exclusive inspection modes without selected-question detail. When compact
review state exists, the desktop result band uses actionable review copy:
`Kontrollera facit`, a compact count such as `6 att granska`, and
`Granska frågorna som saknar rätt svar eller facitsvar.` Export-ready copy must
remain gated by Sir Convert target readiness and replay artifact authority.
Desktop detail navigation uses symbolic Lucide previous/next controls with
accessible labels, no visible `Föregående` / `Nästa` text, and auto-advance
only after backend-confirmed persistence plus fresh Sir Convert replay
projection. `Ändra` opens the normal answer-key editor inside the selected
detail pane, with `Spara facit` for teacher-owned edits and bounded
`Tidigare förslag` detail when the edit began from an advisory suggestion.

### UI Slice Approval Protocol

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
8. files inspection mode with download/save actions gated by replay artifact
   references;
9. report inspection mode;
10. empty, loading, failed, and partial states across the approved surfaces.

Service/runtime wiring is a separate implementation concern and must not be
used as a reason to skip UI slice approval.

### UI Slice Test-Code Contract

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

### Implementation Gate

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

### Live UI Inspection Gate

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

### Breakpoint Composition Contract

Exam Converter follows the Klassrumskartan workspace rule: responsiveness
within breakpoints, not one responsive layout stretched across all breakpoints.
Phone, tablet/narrow-laptop, and desktop are separate approved compositions.

- Phone (`max-width: 767px`): a dedicated reduced companion workflow. It must
  not render the table/detail or navigator/detail compositions. It should show
  one primary review surface at a time, with readable answer-key editing and no
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
reuse the same review projection, normal answer-key editor, durable
correction-session save path, and replay artifact authority.

## Decisions And Interpretation

No implementation authority is created by this reference.
