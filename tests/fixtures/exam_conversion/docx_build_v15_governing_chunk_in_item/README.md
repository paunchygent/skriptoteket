# Governing chunk listed in an item, schema v15

Unedited live replies of two one-family-per-batch `exam-conversion-eval` runs at gpt-6-luna
low reasoning (D37), kept because a converter reply lists a chunk the grouping marks as
governing several questions in one question's `source_anchors` instead of its instructions.
Layout matches `../docx_build_v10/README.md`.

- `svenska_2_kursavslutande_prov_med_facit/`: run d26-real-1fam-low-16. The grouping marks
  body:0074 as governing q18 and q19; reply `docx_w2-06-01` lists it in q18's item and prints
  its text at the start of the item's first body paragraph.
- `bf26_english_1_unit_test_kap_1_2_med_facit/`: run d26-real-1fam-low-17. The grouping marks
  body:0058 and body:0060 as governing q25–q27; reply `docx_w2-07-01` lists body:0058 as an
  instruction and body:0060 in q25's item, whose whole body is that chunk's text.

Second-wave request ids follow the order in which second-pass labels arrived live, so the
tests serve second-wave replies by anchor (`SecondWaveByAnchor`).
