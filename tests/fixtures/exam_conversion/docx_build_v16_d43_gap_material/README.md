# Gap fill keeps the material its line talks about, schema v16 (D43)

Converter output for svenska_2_kursavslutande_prov_med_facit body:0085 to body:0087. Chunk
body:0086 sets four phrases in italics. Two of them are material the student reads, and two
are the answers.

- `low25_docx_w2-08-01.json`: unedited live reply of the eval run d26-real-1fam-low-25. It
  keeps the material as text and makes the two answers gaps.
- `low26_docx_w2-09-01.json`: unedited live reply of the eval run d26-real-1fam-low-26. It
  returns outcome review because it cannot tell which italic phrases are gaps.
- `low28_docx_w2-09-01.json`: unedited live reply of the eval run d26-real-1fam-low-28, made
  with the D43 prompt. It makes all four italic phrases gaps, as the second staging upload did.
- `staging_reconstruction_material_gapped.json`: the second staging upload of 1ed611cb made all four
  italic phrases gaps and kept the item as reviewed. That upload kept no raw reply. This file
  writes the reply the captured document records
  (`.artifacts/staging-walk/39-05-04-1ed611cb/evidence/exam-document-edited.json`, item
  body:0085): every text segment as captured, and every gap with its captured
  accepted_values, which include the forms the converter adds. Its source_anchors are the
  question's three chunks, as in the low-25 reply.
- `gap_fill_items_low23_to_low26.json`: every converted gap_fill item of the recorded replies
  of the eval runs d26-real-1fam-low-23 to d26-real-1fam-low-26 across the eight corpus
  exams, unedited, one entry per line with its run, exam and reply file.
- `scenario.json`: the source exam, the question's anchors, and which reply file shows which outcome.
