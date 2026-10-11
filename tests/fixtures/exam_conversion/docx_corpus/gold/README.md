# DOCX gold files

TASK-SKRIPT-39-05-02 G1-G3 owns these source-authored gold files. Each JSON file
was read from its DOCX and embedded facit, independently of the converter.
`source_sha256` binds the file to the checked source bytes. The user confirmed all eight
files on 2026-10-10; each carries `confirmed: true` and a `confirmation_note`
recording that decision. The same day the user accepted corrections from a blind
second labelling to the English 1, poetry and Solid Gold 3 files. A later change to a gold file needs a new user
confirmation. Unresolved `teacher_questions` prevent confirmation and produce comparison mismatches.

The executable schema is `scripts/exam_conversion_eval/gold.py` (`GoldExam`).
The comparator is `scripts/exam_conversion_eval/compare.py`. A gold file is one
correct conversion, so the comparator judges the eight conversion principles of
TASK-SKRIPT-39-05-03 against it rather than textual identity. Reports keep the
source item labels, the confirmation state and, per exam, the number of items
failing each principle. Comparisons against these confirmed files are the A7
acceptance evidence.

One source-numbered question is one gold item, including all of its subparts.
The poetry quiz's separately labelled Part 2 and Part 3 questions are separate
items. Question numbering and point labels become metadata. Section headings are
not part of item prompts; an item's own heading text, such as poetry
“Part 2A: contemplation”, stays. Section instructions, word banks, letter hints
and relevant reading passages stay in prompts. Choice
options live in `choices`; correct answers never enter student-visible text.
`[___]` marks each response gap in order. A separate response line duplicating
an in-sentence gap is omitted. Matching items preserve the original table
text in the prompt and state the correct directed pairs in `pairs`. Table rows in
prompts drop empty cells, including blank matching answer cells.

Open responses use `free_text` and keep any source grading guidance in notes.
Shapes that fit no supported response kind use `review`, which corresponds to
a native free-text item requiring review. `matching` corresponds to the native
matching kind, whose two lists and directed pairs the comparator reads.

Items are paired with gold by position. A converted item passes when it meets
all eight principles:

1. **Segmentation.** The exam has the gold number of items, and no item holds a
   stretch of five or more words that belongs only to another gold item.
2. **Response kind.** The item has the gold kind; a free-text item requiring
   review counts as `review`.
3. **Response slots.** The item has the gold number of gaps, the same options
   and, for matching, the same two lists, compared by wording.
4. **Scoring.** The correct options equal gold, and the pairs equal the gold
   pairs. Each gap accepts every gold answer, ignoring case and whitespace. An
   extra answer fails when it is another gap's gold answer, or when it is
   neither within the A10 spelling policy in `answer_spelling.py`
   (Damerau-Levenshtein distance at most 1 for a gold answer of up to six
   characters, otherwise at most 2, over the whole answer) nor a form rule 3
   admits: a part of a slash-joined gold answer, or the other half of a
   "short = term" definition in the gold prompt.
5. **Points.** Points equal gold.
6. **No answer leakage.** No gold answer, correct option or matched right
   entry occurs as a whole phrase in the item's title or prompt more often
   than in the gold prompt.
7. **No platform labels.** Options and match entries carry no leading letter or
   number, and the title or prompt carries no opening question number, no
   point label and no printed blank marker beyond what the gold prompt shows.
8. **Content present.** Every line and table cell of the gold prompt, without
   its list label, occurs in the item title, the item prompt or the item's
   match lists. Document instructions do not count, because the Exam.net
   export carries only items. Case, punctuation, quote style, whitespace, line
   breaks and gap markers do not count.

Explicit source facit variants remain gold answers in their own right.

`pdm run exam-conversion-eval --mode recorded --evidence-dir <dir>` converts
every corpus DOCX with the DOCX import job's chunker and converter, compares
each document with its gold file, prints the per-exam and per-item mismatches,
writes `report.json` to `<dir>` and exits non-zero when any item differs.
Recorded mode replays the recorded live responses in
`tests/fixtures/exam_conversion/`, listed per exam in
`scripts/exam_conversion_eval/__main__.py`. `--mode live` calls the configured
provider, reports input and output tokens per exam and writes each round's
response to `<dir>/recordings/` in the recorded fixture format. Live mode is a
manual eval-loop step, not CI. A conversion crash fails the import job, so the
report shows it as an exam that converted no items.

| Source exam                 | Gold items | Points |
| --------------------------- | ---------: | -----: |
| BF26 diagnostic grammar     |        104 |    105 |
| BF26 English 1 chapters 1–2 |         53 |     59 |
| Chapter 4 poetry and lyrics |         28 |     28 |
| Scientific methodology      |         16 |     20 |
| Solid Gold 3 Unit 3         |         73 |     74 |
| Svenska 2 grammar variant 1 |          8 |     38 |
| Svenska 2 grammar variant 2 |          8 |     38 |
| Svenska 2 course exam       |         24 |     36 |
| Total                       |        314 |    398 |

Methodology question 2, “Tidningsartiklar”, keeps the source facit C and D.
The accepted decision keeps B excluded, so the item carries no open
`teacher_questions`; its notes record the decision.
Svenska 2 course questions 1–15 have an inferred one point each from the
15-point section; the user confirmed this inference.
Whole-item points are retained throughout. Partial credit and open-response
rubrics are teacher grading decisions outside this comparator's contract.
