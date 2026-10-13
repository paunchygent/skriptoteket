# A question neither labeling pass labels, schema v16

Live replies of the one-family-per-batch run d26-real-1fam-low-19 on
svenska_2_kursavslutande_prov_med_facit, with one edit, because no live run had a question
that neither labeling pass labeled.

The edit is in `svenska_2_kursavslutande_prov_med_facit/decisions_1.json` only: the first-pass
answer `kind_q20` becomes the refusal `{"type": "refusal", "name": "kind_q20"}`. The live second
pass for q20, `label_b_q20.json`, answers unresolved unchanged, so q20 gets no label from either

Every other file is the live reply unchanged.
