# DOCX gold files

TASK-SKRIPT-39-05-02 G1-G3 owns these source-authored gold files. Each JSON file
was read from its DOCX and embedded facit, independently of the converter.
`source_sha256` binds the file to the checked source bytes. The user confirmed all eight
files on 2026-10-10; each carries `confirmed: true` and a `confirmation_note`
recording that decision. The same day the user accepted corrections from a blind
second labelling to the English 1, poetry and Solid Gold 3 files. A later change to a gold file needs a new user
confirmation. Unresolved `teacher_questions` prevent confirmation and produce comparison mismatches.

The executable schema is `scripts/exam_conversion_eval/gold.py` (`GoldExam`,
`schema_version` `exam_conversion_gold_v2`). `items` holds standalone items and
parents. A parent (`kind: "parent"`) groups consecutive questions of one response
kind that sit under one source section instruction. It carries `source_label`,
the shared `instruction` and `children`, each a complete item whose `prompt`
omits the instruction lines. A parent's points are the sum of its children's
points and are not stored. A question that shares its instruction with no
neighbour stays a standalone item. Source labels are unique across standalone
items, parents and children. `scripts/exam_conversion_eval/move_gold_to_parents.py`
performed the one-off move from v1.
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

A conversion is correct when a student on Exam.net meets the same questions,
answers them the same way and is scored the same as on paper, and the
conversion adds nothing Exam.net owns and nothing that reveals an answer. The
comparator judges these eight principles per question, a standalone item or a
child of a parent, and pairs gold and converted questions by position. A
question's text is its parent's instruction, its title and its body.

Wording is compared as a sequence of casefolded words and response gaps. Case,
punctuation, quote style, whitespace and line breaks do not count. Each line and
table cell of a gold prompt or instruction, without its list label, is a
phrase. A gold table in a matching prompt is read in source order as the two
lists (a two-cell row gives its left then its right entry; a single cell is a
left entry when it is a gold pair's left text, otherwise a distractor) and is
not a body phrase.

1. **Segmentation.** One source question is one item with all its subparts, in
   source order; no source text is lost, duplicated or attached to the wrong
   item. The exam has the gold number of questions. Each question sits under the
   same parent as its gold siblings, or under none (the partition of question
   positions into parents must equal gold's). A gold body phrase found in the
   converted body only before the position the walk through the gold phrases has
   reached fails as out of order; a phrase found in the title does not move the
   walk, so a heading may sit in the title or the body. A gold phrase that occurs
   more often across the converted title, instruction, body and list entries
   than across the gold instruction, prompt and lists is duplicated. A whole gold
   phrase of another question that the gold question's own text does not contain,
   but the converted question's text does, is foreign. No word-count minimum
   applies.
2. **Response kind.** The item has the gold kind; a free-text item requiring
   review counts as `review`.
3. **Response slots.** The item has the gold number of gaps, and every gold
   phrase that holds a gap holds it in the same place. Choices equal gold as an
   ordered list by wording, so order and multiplicity count. A matching item's
   left and right lists equal the gold table's two lists in source order.
4. **Scoring.** The correct options equal gold as a set of wordings, and the
   pairs equal the gold pairs. Each gap accepts every gold answer, ignoring case
   and whitespace. An extra answer fails when it is another gap's gold answer, or
   when it is neither within the A10 spelling policy in `answer_spelling.py`
   (Damerau-Levenshtein distance at most 1 for a gold answer of up to six
   characters, otherwise at most 2, over the whole answer) nor a form rule 3
   admits: a part of a slash-joined gold answer, or the other half of a
   "short = term" definition in the gold instructions or prompt.
5. **Points.** Points equal gold; a parent's points are the sum of its
   children's.
6. **No answer leakage.** No answer occurs as a whole phrase in the converted
   title or body more often than in the gold prompt. Answers are the gap values,
   the correct options and the matched right entries; for free-text and review
   questions they are also the teacher's facit, the text after the last
   "Label:" of each line of the gold notes. The instruction does not count.
7. **No platform labels.** Options and match entries carry no leading letter or
   number. The number of title and body lines that open with a question number
   does not exceed the gold count, and the instruction, title and body carry no
   more point labels and printed blank markers than gold shows.
8. **Content present.** Every gold phrase occurs in the converted title,
   instruction or body; the parent's instruction phrases occur in the converted
   parent's instruction. A phrase holding a gap is compared without the gap
   markers here; where the gap sits is principle 3.

The exam title is judged beside the eight principles and is required for an exam
to pass (D12). The converted title equals the gold title, or equals the source
heading alone, or the source heading with its printed subtitle. The heading is the
source chunk whose words equal the gold title, or whose words with the next
chunk's words equal it, and the subtitle is the chunk after it.

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
