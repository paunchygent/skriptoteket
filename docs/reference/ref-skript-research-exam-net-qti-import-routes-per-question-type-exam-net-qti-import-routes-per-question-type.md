---
type: reference
id: REF-SKRIPT-RESEARCH-exam-net-qti-import-routes-per-question-type
title: Exam.net QTI import routes per question type
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: draft
reference_kind: research
summary: Probed Exam.net QTI 3.0 import behaviour per question type, with the QTI
  route the export uses and what the teacher completes after import
---

## Research Purpose And Boundary

Question: which Exam.net question type, answer key, points and scoring rules
does a QTI 3.0 package produce through Exam.net's "Importera QTI-prov (BETA)"
import, and what does the teacher have to complete by hand afterwards?

The findings inform the export routes planned under ST-SKRIPT-39-06 (teacher
authoring of every Exam.net question type). This document records observed
import behaviour only; it decides no export route.

Scope: QTI 3.0 packages with standalone items, imported 2026-10-14 and
2026-10-15. QTI 1.2 is rejected by Exam.net and is out of scope. Student-side
behaviour and automatic marking of submitted answers were not observed.

## Evidence And Sources

- Probe rounds 13–18: 117 standalone items, V47–V59 and V60–V137, built by
  generator scripts on the HuleEduOS converter helpers
  (`scripts.converters.build_qti3_package`). They were imported into Exam.net
  and read back through `/api/exams/automarked/<exam id>/questions`, at task
  level (`answers`, `gradingRules`). The test exams are 5332727 (round 13),
  5332858 (14), 5332874–5332877 (15), 5332898 (16), 5332910 (17) and
  5332951 (18).
- Reference exam 5325595, written by hand by the teacher: one Matcha ihop, one
  Kategorisera, one Enkelt svar and one Fritext item with rubric criteria.
  Its rule data is the comparison baseline for the teacher defaults.
- Inherited evidence (not repeated here): HuleEduOS
  `docs/reference/ref-eduos-general-exam-net-import-probe-ledger-exam-net-import-probe-ledger.md`
  (rounds 1–12: V1–V46; slider, media and extended-text variants) and
  `.codex/skills/examnet-qti-import/references/examnet-qti3-contract.md`.
- The teacher observed in the Exam.net editor that the Fritext field
  Svarsalternativ is not shown to students, and that each rättningskriterie
  label is editable text.

## Findings And Interpretation

### Exam.net rule data

A scoring rule is stored as `{correct, wrong, point, label}`, and the rules of
a task are summed.

- `wrong: -1` means any number of wrong answers is allowed.
- Imported rules for pair and count items carry `correct: N, wrong: -1` with
  the generated English label "At least N correct, and max N-1 wrong". The
  label is text only: the stored data is the same as the teacher default "Minst
  N korrekt, och max alla fel", which is one point per correct answer with no
  penalty.
- The teacher's own Fritext criteria carry `correct: -1, wrong: 0` with the
  criterion text as label.

### Kategorisera (categorizingItems)

- Route: `qti-match-interaction`. The first match set becomes the rows and the
  second the columns.
- Many-to-many keys are imported with every tick keyed: V51 had 5 ticks worth
  5 points.
- Surplus choices in the column set become columns that no row uses (V47).

### Matcha ihop (matchItems)

- Route: `qti-associate-interaction` keys the pairs correctly. In all 22
  associate variants (V48, V52–V56, V66–V80), Exam.net lists every choice in
  both columns and again among "Ytterligare felaktiga svar", whatever the
  match-group, match-max/min, fixed, shuffle, choice order or key direction.
  No QTI attribute was found that gives the teacher-made layout (terms left;
  properties and distractors right).
- Route: `qti-order-interaction` gives clean sides, but the right column holds
  the position numbers 1..N instead of words (V60–V65). It has one ALL_CORRECT
  rule.

### Points and rules from response processing

- Exam.net reads the response mapping, not the response processing.
- A uniform mapped value v gives one rule row per correct entry at v points.
  2 per pair gives 6 points (V84, V85); 0.5 per pair gives 1.5 (V97).
  MAXSCORE is ignored when such a mapping is present (V85, V86).
- No mapping, an uneven mapping or negative mapped values give one ALL_CORRECT
  rule worth MAXSCORE (V81, V83, V87, V89, V90). Without outcome declarations
  that rule is worth 1 point (V88).
- Custom tiered response processing is ignored (V81–V83). Tiered rules can
  only be set in Exam.net after import.

### Enkelt svar (simpleAnswer)

- No construction produced a keyed Enkelt svar. Media interactions import as
  Enkelt svar with an empty key (V57, V58), as slider and extended-text did in
  the HuleEduOS ledger.
- A standalone `qti-text-entry-interaction` with a uniform mapping imports as
  Lucktext (fillGaps) with one gap, all accepted answers keyed and 1 point
  (V99–V104, V108). Without a mapping it keeps the correct value at 0 points
  (V98, V105–V107, V109).
- Hottext imports as Flerval (multipleChoice) (V111). A custom interaction is
  dropped with an import warning (V112).

### Fritext (freeText)

- `qti-extended-text-interaction` imports as Fritext. Points come only from
  the response declaration:
  - a uniform 1-point mapping with k entries gives k points and k rule rows
    (V110, V126–V128). Uneven values give 0 points and no rules (V129);
  - a correct response without a mapping gives one CORRECT_ANSWER rule worth
    MAXSCORE (V135–V137);
  - MAXSCORE or normal-maximum alone gives 0 points (V113, V114).
- Criterion text never reaches Exam.net. It was tried as mapping keys
  (V126–V129), as correct-response values with single, multiple and ordered
  cardinality (V130–V134), and as the interpretation attribute (V133). Rule
  labels are always generated, and the teacher retypes them.
- Every rubric block, modal feedback and feedback block becomes a separate
  information block (V59, V115–V122, V124). Students may see these blocks;
  that was not observed.
- Svarsalternativ is stored in the task `answers` string. No construction
  filled it (V130–V137). It is hidden from students, so the teacher can paste
  the rubric there after import.

## Evidence Gaps And Follow-Up

- Whether students see the information blocks that rubric and feedback
  constructions produce was not checked in the student view.
- Automatic marking of submitted student answers against the imported rules
  was not observed.
- The export routes and the teacher's post-import checklist are planned under
  ST-SKRIPT-39-06. The teacher's direction recorded on 2026-10-15 is input to
  that planning:
  - grid only for matching;
  - many-to-many grids;
  - Enkelt svar as a one-gap Lucktext;
  - Fritext as 1-point criterion rows, with the criterion text in a checklist
    on the export screen.
