# Repeated type conflict, schema v10

Live replies from an earlier `exam-conversion-eval` run of the type-batched pipeline on
one corpus exam, kept because its converter reported a type conflict in batch `w2-05-01` and
again in that batch's resend `w2-05-01c01`; `w2-05-01c01c01` is a reply the pipeline must
never request. Layout matches `../docx_build_v10/README.md`.

One reply is edited. In the live run the second pass answered `unresolved` for q20, and the
route of that time converted an unresolved question as free text. Since D23 was revised on
2026-10-12, an unresolved question converts with the first pass's top label (gap_fill), so the
recorded free_text batch replies would no longer reach it.
`svenska_2_kursavslutande_prov_med_facit/label_b_q20.json` therefore answers `free_text`
instead of `unresolved`. Every other file is the live reply unchanged.
