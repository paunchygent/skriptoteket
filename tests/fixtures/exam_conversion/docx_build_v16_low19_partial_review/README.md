# A failed item that lists only part of its question, schema v16

Live replies of the one-family-per-batch run d26-real-1fam-low-19 on
svenska_2_kursavslutande_prov_med_facit, with one edit, because after the own-chunk repair no
live reply leaves a failed item holding only part of its question.

The edit is in `svenska_2_kursavslutande_prov_med_facit/docx_w2-09-01.json` only: the item's
`source_anchors` lose body:0086, leaving body:0085 and body:0087. `answer_key_anchors` still
lists body:0086, so admission keeps body:0086 as a teacher note. The grouping gives body:0085
and body:0086 to the question as its own chunks. The item has kind gap_fill and no gap, so it
fails the native contract.

Every other file is the live reply unchanged.
