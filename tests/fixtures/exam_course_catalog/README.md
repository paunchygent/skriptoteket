# Recorded Skolverket inputs

Captured from the keyless Skolverket Syllabus API on 2026-10-16 by the task lead.
The retained originals are in session `01a145b6-c404-761f-aeef-39de058ba7ca`,
`evidence/discovery/`.

- `courses-gy.json`: eight unchanged course records from the GY/LATEST response.
- `subjects-gy.json`: their seven unchanged subject records from GY/LATEST.
- `subjects-gr.json`: Svenska and Moderna språk from GR/LATEST.
- `subj-GRGRSVE01.json`, `subj-GRGRMSP01.json`: full recorded detail responses.
- `subj-GRGRBIO01.json`: full detail response fetched by the navigator on
  2026-10-16 from `/v1/subjects/GRGRBIO01`; an introductory heading precedes the
  year-band heading in the first two central-content sections.

- `course-*.json`: the eight catalog fixture courses' `course.centralContent`
  objects, recorded unchanged from `/v1/courses/{code}` on 2026-10-17 for
  TASK-SKRIPT-39-08-03. Other response fields were excluded; these are real
  Skolverket bullets, not generated curriculum text.

Tests mutate validity dates explicitly to challenge date boundaries; those
mutations are synthetic cases, not claims about Skolverket's published dates.
The Moderna språk recording includes repeated year bands with language-specific
headings, so deduplication must not duplicate the subject-and-band keys.
