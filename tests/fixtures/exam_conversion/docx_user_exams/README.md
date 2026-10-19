# User exams with live DOCX producer recordings

Two teacher exams the user supplied for TASK-SKRIPT-39-04-12, a mixed exam with
dominating free-text items: `omprov_grammatik_sve2.docx` and
`exempelprov_grammatik_sve2_v2_1.docx`. They live outside `docx_corpus/`
because that corpus requires a human-confirmed gold file per exam; these have
none. Their replay assertions encode the user's rulings of 2026-10-18 instead.

`recordings/<stem>/` was recorded on 2026-10-18 in the local dev web container
from revision `4717a9d3` with `scripts.exam_conversion_eval` providers and
default settings (`LLM_DOCX_BATCH_FAMILIES=16`). No credentials are stored here.

| Exam                            | Items | Input tokens | Output tokens |
| ------------------------------- | ----: | -----------: | ------------: |
| omprov_grammatik_sve2           |     9 |       47,516 |         9,267 |
| exempelprov_grammatik_sve2_v2_1 |     9 |       64,889 |         9,809 |

2026-10-18 (TASK-SKRIPT-REP-0046): each `recordings/<exam>/label_b_<qid>.json` carries the request source text it answered in `label_b_<qid>.request.txt`, followed by one final newline; the replay serves a label reply only to a request ending in that text. The 15 keys were derived without live calls by replaying both exams through the production pipeline and taking each `item_type_label` request's text after `### Question q1`. At the capture revision `4717a9d3`, the 7 `exempelprov_grammatik_sve2_v2_1` keys equal the committed sidecars. The 8 `omprov_grammatik_sve2` requests began with their part heading line at `4717a9d3`, so those recordings were stale. On 2026-10-19 the user decided to re-record them, and they were re-recorded live against today's requests, once each with `gpt-6-luna` (9,139 input and 941 output tokens). All 8 labels are unchanged (TASK-SKRIPT-REP-0046).
