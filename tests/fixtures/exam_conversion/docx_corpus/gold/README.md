# DOCX gold files

TASK-SKRIPT-39-05-02 G1-G3 owns these source-authored gold files. Each JSON file
was read from its DOCX and embedded facit, independently of the converter.
`source_sha256` binds the file to the checked source bytes. The user confirmed all eight
files on 2026-10-10; each carries `confirmed: true` and a `confirmation_note`
recording that decision. A later change to a gold file needs a new user
confirmation. Unresolved `teacher_questions` prevent confirmation and produce comparison mismatches.

The executable schema is `scripts/exam_conversion_eval/gold.py` (`GoldExam`).
The comparator is `scripts/exam_conversion_eval/compare.py`. It compares
ordered items, kind, points, prompt, choice sets, correct-choice sets, each
gap's accepted answers, and directed matching pairs. Reports keep the source
item labels and the confirmation state. Comparisons against these confirmed
files are the A7 acceptance evidence.

One source-numbered question is one gold item, including all of its subparts.
The poetry quiz's separately labelled Part 2 and Part 3 questions are separate
items. Question numbering and point labels become metadata. Section instructions,
word banks, letter hints and relevant reading passages stay in prompts. Choice
options live in `choices`; correct answers never enter student-visible text.
`[___]` marks each response gap in order. A separate response line duplicating
an in-sentence gap is omitted. Matching items preserve the original table
text in the prompt and state the correct directed pairs in `pairs`.

Open responses use `free_text` and keep any source grading guidance in notes.
Shapes that fit no supported response kind use `review`, which corresponds to
a native free-text item requiring review. `matching` is a gold kind already;
its native implementation belongs to the later matching task.

Prompt, option and matching text comparison normalises whitespace. Gap
answers additionally ignore case. Every facit answer must remain present;
an extra answer passes only the parent-decided A10 spelling policy in
`answer_spelling.py`: Damerau-Levenshtein distance at most 1 for a gold
answer of up to six characters, otherwise at most 2, over the whole answer.
An extra answer equal to another gap's gold answer in the same item fails.
Explicit source facit variants remain gold answers in their own right.

Eval command wiring, recorded provider replay and live token reports wait for
TASK-SKRIPT-39-05-01 to merge to main and for the parent to merge main into
this task branch. This slice makes no converter or live-eval claim.

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
