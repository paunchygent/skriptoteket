# Governing heading, schema v15

Live replies of the one-family-per-batch run d26-real-1fam-low-17 on
svenska_2_kursavslutande_prov_med_facit, with one edit, because no live grouping marked a
heading as a governing context.

The edit is in `svenska_2_kursavslutande_prov_med_facit/docx_grouping_1.json` only:

- `shared_contexts` gains, first, `{"anchor": "body:0006", "scope": "section_instruction",
  "owner": "exam", "governs": ["q1", …, "q15"]}`, the same governs list as body:0009.
  body:0006 is the heading chunk "Del 1: litteraturhistoria, 15 poäng".
- `other_anchors` loses body:0006, so the heading has one place in the grouping.

Every other file is the live reply unchanged. Reply `docx_w1-01` lists body:0006 and body:0009
as instructions.
