# User exams with live DOCX producer recordings

Two teacher exams the user supplied for TASK-SKRIPT-39-04-12, a mixed exam with
dominating free-text items: `omprov_grammatik_sve2.docx` and
`exempelprov_grammatik_sve2_v2_1.docx`. They live outside `docx_corpus/`
because that corpus requires a human-confirmed gold file per exam; these have
none. Their replay assertions encode the user's rulings of 2026-10-18 instead.

`recordings/<stem>/` was recorded on 2026-10-18 in the local dev web container
from revision `4717a9d3` with `scripts.exam_conversion_eval` providers and
default settings (`LLM_DOCX_BATCH_FAMILIES=16`). No credentials are stored here.

| Exam | Items | Input tokens | Output tokens |
| --- | ---: | ---: | ---: |
| omprov_grammatik_sve2 | 9 | 47,516 | 9,267 |
| exempelprov_grammatik_sve2_v2_1 | 9 | 64,889 | 9,809 |
