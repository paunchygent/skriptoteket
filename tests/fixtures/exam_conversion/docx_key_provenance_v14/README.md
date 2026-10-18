# Live DOCX producer recordings — key provenance v14

Recorded on Hemma staging on 2026-10-14 from revision `c270419e` with
`scripts.exam_conversion_eval`, all eight committed corpus exams, and
`LLM_DOCX_BATCH_FAMILIES=16`. The runner used the staging web container's provider
configuration and inherited API key. No credentials are stored here.

`docx_*.json` retain the recorded provider content keyed by request ID, with
structural migrations to the current v14 contract: task 39-09-04 replaced
Fritext marking guides with criteria, and task 39-09-06 removed model spelling
candidates. Automatic misspellings now come from the committed deterministic
producer at replay time; they are not new model observations.
`decisions_N.json` are unmodified Decisions replies in request order. Directory
versioning identifies the strict `docx_exam_build_v14` producer contract, not a
promise that every producer reply passes admission or matches gold.

The live eval reported **0/8 exams matching gold** and no conversion crashes.
Replay tests exercise current admission, provenance, spelling, and failure
contracts; these recordings are not an approved gold reference. Known model
quality findings, source-classification audit, exact token usage and full eval
report are retained in session `01a13a87-acac-7730-bb4e-746618d73cfd`, under
`evidence/implementation/TASK-SKRIPT-39-05-10/backend/recording-refresh/`.

| Exam | Input tokens | Output tokens |
| --- | ---: | ---: |
| Diagnostic grammar | 88,911 | 27,419 |
| BF26 English | 107,347 | 15,820 |
| Poetry and lyrics | 24,978 | 8,786 |
| Vetenskaplig metod | 18,945 | 9,062 |
| SA24 Solid Gold | 60,869 | 17,776 |
| Svenska grammar variant 1 | 38,681 | 9,193 |
| Svenska grammar variant 2 | 48,881 | 10,513 |
| Svenska course final | 38,804 | 8,689 |
| **Total** | **427,416** | **107,258** |

These are the eval runner's reported conversion token counts, not a separate
measurement of Decisions-service billing.

2026-10-17: recorded BF26's current `docx_w2-10-01c01` typed resend on Hemma staging revision `d92b828e` with `gpt-6-luna` as `docx_w2-11-01c01.json` (after its original conflict recording); the reply repeats a type conflict, using 3,571 input and 373 output tokens (3,944 total).

2026-10-18 (TASK-SKRIPT-REP-0045, user ruling 2026-10-18): re-recorded the 14 Svenska second-pass labeler replies whose requests changed when points lines joined their questions (`c67dcb70`): variant 1 `q2`, `q5`, `q6`, `q7`; variant 2 `q1`-`q7`; course final `q21`, `q22`, `q24`. Each request body was forwarded byte-identically from the current pipeline to the provider with `gpt-6-luna`, once each, using 16,286 input and 1,315 output tokens (17,601 total). Variant 2 `q5` now answers `gap_fill` (previously `free_text`); the other 13 labels are unchanged. Every `label_b_<qid>.json` carries the request source text it answered in `label_b_<qid>.request.txt`, followed by one final newline; the replay serves a label reply only to a request ending in that text.
