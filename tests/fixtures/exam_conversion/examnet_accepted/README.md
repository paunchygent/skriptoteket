# Exam.net-accepted QTI package (TASK-SKRIPT-41-02-01)

The QTI 3.0 package Skriptoteket exported and Exam.net accepted on import as
exam 5345261: `svenska2-rev11-qti.zip` (8,939 bytes).

Exam.net offers no exam-content export (Mac parent check 2026-10-19), so this
committed export stands in for an Exam.net export: it is the exact bytes
Exam.net imported, and the test proves they import back into the workspace.

Provenance: exported from Skriptoteket main revision `1f9e4367` (the Svenska 2
rev11 workspace exam, 24 items totalling 36 points) with
`GET /exports/qti?expected_revision=11`; imported into Exam.net as exam
5345261 during the 1f9e4367 staging proof ("Importerade och behöver granskas":
question 1 = Del 1 with 15 parts, questions 2-6 standalone, question 7 = Del 3
with 4 parts, 36p). Proof: `evidence/staging-proof-1f9e4367/proof.md` steps
8-9 in session `01a149c9-5bc7-7713-ba64-12dee0470bdd` (source checkout only;
the v6 source document it cites is not committed here).

`svenska2-rev11-qti.zip.sha256` holds the package digest in the same
`<hex>  <filename>` format as `real_inputs/*.sha256`.

`svenska2-rev11-expected.json` is the expected import, derived once from the
v6 source document named above (schema `native_exam_document_v6`; never loaded
into the current model, and the repo keeps no readers for it). Per item in
order: kind, points, plain prompt text (v6 bodies rendered the way
`body_plain_text` renders them, gap segments as `[___]`), and the answer-key
projection (correct choices by position, gap accepted and automatic values,
inline dropdown options with the correct position, match pairs, print order,
free-text rubric criteria). Per parent: child positions and
instruction text. The source document instructions are empty, so no
instruction folding applies.
