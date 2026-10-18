"""The DOCX build prompt: a shared core plus one section per item kind in the batch.

Each section states the general principles of its kind and shows them with short constructed
examples. A batch receives only the sections for its item_kinds; the core still names every
kind so the model can report a question whose kind the batch was not given.
"""

from __future__ import annotations

from functools import cache

from skriptoteket.domain.curated_apps.exam_workspace.item_kind_boundary import (
    converter_kind_rule,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)

_CORE = """You convert one part of a teacher's exam into the JSON envelope. The part arrives as
ordered source chunks.

The input
- chunks are the chunks this part converts: its questions and the exam title, headings,
  instructions and facit lines that belong to them.
- context_chunks belong to other parts: a shared instruction or passage, or the other questions
  of a section whose heading, instruction or points line this part holds. Read them to
  understand the questions in chunks and to tell a line that serves a whole section from a line
  that belongs to one question. Their questions and wording are converted by their own part.
- Chunk text marks the teacher's italics as <i>...</i> and each source picture as
  <image asset_id="..."/>. The <i> tags show formatting: every output field, facit_text and
  accepted_values included, carries the words without the tags.
- item_kinds lists the kinds of question this part holds.
- questions lists each question in chunks as the anchors of its own chunks, in source order.

Where each chunk goes
Every chunk in chunks goes to exactly one place: one item's source_anchors, the exam title,
an instruction or answer_key_anchors. This holds up to the last chunk, also after the last
question.
- The exam title is the document's opening heading, copied verbatim.
- Each question in questions becomes exactly one item, and an item holds one question. Its
  numbered sentences, lettered parts and lines stay in that one item, also when each of them
  asks the student for an answer.
- An item is one question with every line printed for it alone: its heading or label line,
  an instruction, word list or passage printed only for this question, its stem, options,
  blanks, pictures and its own points line. A heading or label line printed for one question,
  such as "Question 3 (2 points)" or "Part B: term (1 point)", belongs to that question: its
  wording without the question number and points is the first paragraph of the body, and its
  points are the question's points.
- An instruction is text printed once for several questions: a heading above two or more
  questions, a section instruction, a word bank or a shared passage. Copy it verbatim. The
  converter places it above the questions it serves, so their bodies leave it out.
- A facit chunk holds the teacher's answers. A chunk is facit by its position: it stands under
  a facit heading, or it is an answer line that follows a question. Its anchor goes in
  answer_key_anchors. A chunk that holds question text together with an inline answer is
  question text and goes in that item's source_anchors.
- points is the number printed for the question itself, as an integer, and null when the source
  prints none. A points line after a question's last line is that question's points, also when
  the question has lettered parts; its anchor joins the question's source_anchors. A total on a
  section heading, or on a points line after a run of questions that print no points of their
  own, belongs to the run: report it as an instruction with that line's anchor and the total
  as its points.

Building an item
- An item's body is the wording of its own source_anchors: every word, in order. Wording a
  question prints in its own chunk is its text, also when another question prints the same
  wording. Before writing each body, find the item's own chunks again and copy from them.
- Student-visible text (the body, choices, exam title and instructions) is the source wording.
  The body leaves out the printed points and the number or letter that orders the questions;
  printed_label holds that number or letter as printed, with its word ("Fråga 3",
  "Question 4", "3", "a"). A part or section name such as "Part 2" or "Del B" is body or
  instruction wording.
- A part label such as "a)" or "b)" inside one question names a part of that question: the
  student's answer and the facit refer to it. It stays in the body exactly as printed, in its
  place, with the words after it.
- A source picture becomes an asset segment with its asset_id at the same place among the
  body's text and gaps; a picture-only chunk becomes a paragraph of asset segments. A chunk of
  kind drawing is a picture without text and joins the source_anchors of the question it
  stands with. A picture in a facit chunk stays with that chunk in answer_key_anchors.
- Each text segment holds text. A printed answer line or empty answer space in a kind without
  gaps is answer space, not question text.

The facit and the key
- facit_text copies the teacher's answers for this question verbatim, wherever the source
  prints them: a facit line, a facit section, or inline in the question itself. It includes
  every line, note and listed alternative such as "Also accepted: …". It is null only when the
  source prints no answer for this question.
- Inline facit: a question line can carry its own answer, set apart by formatting (usually
  italics) or after an answer label ("Label: value"). Italic words that complete the statement
  the student is asked to complete or decide are its answer. Italic material the question gives
  the student to read, such as an example sentence or a phrase the line goes on to name or
  describe, is question text. A bracketed cue in the question's plain text is question text.
  When you cannot tell which marked phrases the student writes, return outcome review with a
  review_reason that names them.
- Facit words are answers: they go into the item's key (accepted_values, correct choices,
  match_pairs or criteria), and student-visible text holds the question. A label that
  introduces the teacher's answer, such as "Svar:", "Facit:" or "Correct answer:", belongs
  to the facit with its answer.
- key_source is copied when the key copies the facit's answer words, including a facit letter
  mapped to its option and listed alternatives split apart; interpreted when you extract
  answers from a facit sentence or build pairs from prose; invented when you solve an objective
  question that has no facit entry. Use the facit whenever it exists. Copied and interpreted
  keys have facit_text; an invented key has none. free_text and an item without a key have
  key_source null.

Kinds
A question's kind follows from how the student answers:
- single_choice: the student picks one option. multiple_response: one or more options.
- matching: the student pairs each entry of one list with a category of another list.
- gap_fill and free_text: {kind_rule}
When a question's kind is not in item_kinds, return it with outcome type_conflict,
conflict_kind set to its kind, its source_anchors and its body.

Every question in chunks is returned in this response. When a question cannot be converted
faithfully, return outcome review with a short Swedish review_reason naming the problem,
together with its source_anchors and body.

The examples below show source lines, the facit and the resulting body, with each gap
written as [gap: accepted values]."""

_CHOICE = """single_choice and multiple_response items
- The body holds the stem. choices hold each option's wording in source order, without its
  ordering letter or number.
- correct marks each option the facit keys; a facit letter or number points to its option.
  single_choice has exactly one correct option, multiple_response one or more.
- A blank in the stem marks where the chosen option goes: it is stem text, copied as printed.
Example: stem "1. Which planet is closest to the sun? (1 p)", options "A. Venus",
"B. Mercury", "C. Mars", facit "B". Result: printed_label "1", body "Which planet is closest
to the sun?", choices Venus, Mercury (correct), Mars, points 1, key_source copied,
facit_text "B"."""

_GAP_FILL = """gap_fill items
A gap_fill body is the question's text with one gap segment at each place the student
writes an answer.

Which places are gaps
Each answer the facit gives is one gap. A sentence holds as many gaps as it has answers.
The source shows the answers in one of these ways:
- a blank in the question (an underscore run, a dotted line or empty brackets) whose answer
  stands in the facit;
- the question printed with its answer filled in and set apart by italics, bold, colour or
  position;
- an answer line "Label: value" whose field the question asks the student to produce: the
  label is text and the value is the answer. A phrase printed after a field label is given
  material unless the question's instruction asks the student for it; it stays text and is
  never a gap.
- a facit that repeats the question's text with an answer after each piece the answers are
  about, such as a label after each word, clause or part of a word.
What the question asks the student to write decides which places are gaps. A field or
phrase the question hands over so the student can answer about it is text with its value,
also when that value is italic or reads like an answer.

Where each gap goes
A gap goes where the student's answer belongs in reading order: directly after the smallest
piece of text the answer is about.
- An answer to a printed blank: the gap takes the blank's place.
- An answer about one word, phrase, clause or part of a word: the gap follows that piece.
  When the facit splits the text into pieces, the pieces are text in their printed order,
  with a gap after each piece that has an answer.
- An answer about the whole sentence: the gap follows the sentence's last word.
- An answer to the whole question, such as a rewritten sentence: the gap is a paragraph of
  its own below the question.
A line holding only a blank, right after a sentence that already has its blank, repeats that
answer place.

What stays text
Every word the student reads stays text in its printed order: the words around each gap,
the pieces the answers are about, the + signs or other marks between them, and every cue.
This holds also when the student's answer translates, rewrites or replaces those words: the
student still needs to read them.
A cue is a hint printed for the student, such as a first letter, a word count, or a word or
phrase in brackets, often in another language. It stays where it is printed, with its
brackets and all of its words, before or after the gap.

The answers
A gap's accepted_values are every form the facit accepts for that answer: the main answer
and each alternative it lists, also after "Also accepted", "or" or a slash. Add as well each
part of a form that joins alternatives with a slash, a short form an instruction defines
("short form = term"), both apostrophe spellings, the keyboard spelling of a typographic
quote, and a sentence of three or more words with and without its closing full stop.

Examples
1. Source "She ___ to school and ___ home at four. (walk, come)", facit "walks, comes".
   Body: She [gap: walks] to school and [gap: comes] home at four. (walk, come)
2. Source "We have lived here ___. (i tio år)", facit "for ten years".
   Body: We have lived here [gap: for ten years]. (i tio år)
   Under the instruction "Translate the words in brackets", source "They ___ (har ätit)
   already.", facit "have eaten".
   Body: They [gap: have eaten] (har ätit) already.
3. Source "Name the word class of each word: The old dog sleeps.", facit "The (article) old
   (adjective) dog (noun) sleeps (verb)".
   Body paragraph 1: Name the word class of each word:
   Body paragraph 2: The [gap: article] old [gap: adjective] dog [gap: noun] sleeps [gap: verb]
4. Source "Rewrite in the past tense: I eat breakfast at seven.", facit "I ate breakfast at
   seven."
   Body paragraph 1: Rewrite in the past tense: I eat breakfast at seven.
   Body paragraph 2: [gap: I ate breakfast at seven. | I ate breakfast at seven]
5. Source "The capital of Australia is ___ (C…).", facit "Canberra (Also accepted: Canbera)".
   Body: The capital of Australia is [gap: Canberra | Canbera] (C…).
   facit_text: Canberra (Also accepted: Canbera)"""

_MATCHING = """matching items
- The body holds the question's instructions; the two lists go into match_left and
  match_right.
- match_left holds the entries the student sorts, in source order. match_right holds every
  category the student chooses among, also categories no entry uses. Both are copied without
  their numbers or letters.
- match_pairs holds every pairing the facit gives: the match_left entry and the match_right
  entry its letter or number points to. An entry the facit pairs with several categories has
  one pair for each.
- An empty answer cell in the table is answer space, not a gap.
Example: "Match each animal with its class: 1. eagle 2. salmon 3. frog. A. fish B. bird
C. amphibian", facit "1B, 2A, 3C". Result: match_left eagle, salmon, frog; match_right fish,
bird, amphibian; pairs eagle-bird, salmon-fish, frog-amphibian."""

_FREE_TEXT = """free_text items
- The body holds the question as printed.
- criteria hold the grading guidance the facit states for this question, in its order: one
  criterion per criterion the key states, with the whole points the key gives it, and its
  wording without the points or the facit label. A guide without per-criterion points is one
  criterion that holds the whole guide, with points null. Without guidance, criteria is empty.
  Points are copied as the key states them.
- When the facit answers a lettered part, that answer goes into criteria after the part's
  label, and the part label with its question stays in the body.
Example: "3. Explain why the seasons change. (2 p)", facit "Earth's axis is tilted (1 p).
The angle of sunlight changes over the year (1 p)." Result: body "Explain why the seasons
change.", points 2, criteria "Earth's axis is tilted" (1) and "The angle of sunlight changes
over the year" (1), facit_text the whole facit."""

_SECTIONS: tuple[tuple[frozenset[NativeExamItemKind], str], ...] = (
    (
        frozenset({NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE}),
        _CHOICE,
    ),
    (frozenset({NativeExamItemKind.GAP_FILL}), _GAP_FILL),
    (frozenset({NativeExamItemKind.MATCHING}), _MATCHING),
    (frozenset({NativeExamItemKind.FREE_TEXT}), _FREE_TEXT),
)


@cache
def docx_build_prompt(kinds: frozenset[NativeExamItemKind]) -> str:
    """The core and the section of each kind in the batch, in a fixed order."""
    core = _CORE.replace("{kind_rule}", converter_kind_rule())
    sections = [text for covered, text in _SECTIONS if covered & kinds]
    return "\n\n".join((core, *sections))
