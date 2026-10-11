# DOCX conversion recordings, schema v10

Live replies from one `pdm run exam-conversion-eval` run of the type-batched pipeline
(TASK-SKRIPT-39-05-04) over every corpus DOCX, one directory per exam:

- `docx_grouping_1.json`: the grouping reply.
- `decisions_N.json`: the Decisions first-pass label replies, in request order.
- `label_b_<question>.json`: the second-pass label reply for one question.
- `docx_<batch>.json`: the converter reply for one type batch; a `c01` suffix is a
  type-conflict resend.

Responses replies are keyed by request id, so a replay serves each request its own reply.
