"""The one written definition of the gap_fill/free_text boundary (TASK-SKRIPT-39-05-08).

The item-type labeler's label descriptions and the DOCX converter's kind rule are both
generated from the two definitions below, so the labeler and the converter can never define
the boundary in different words. The boundary is how the answer is scored (D15 of
TASK-SKRIPT-39-05-04): a response slot checked against accepted strings is gap_fill, whatever
the length of those strings, and a written response the teacher judges is free_text. An
answer key that lists alternative sentences for one answer line keys accepted strings, so it
is gap_fill.
"""

GAP_FILL_DEFINITION = (
    "Each response slot (a blank, a blank line or a labelled field) is checked against one "
    "or more accepted strings of any length, including a whole sentence, a word from a "
    "supplied bank, and an answer key that lists alternative sentences for one answer "
    "line: each listed sentence is one accepted string for that line's slot. In a source "
    "with answers, a blank may be printed already filled with its answer, marked by "
    "formatting such as italics, bold or colour, or set apart by position: that place is "
    "a slot keyed by those words. When the key prints a sentence with a label after each "
    "of its units, or a word split into parts joined with + and a label after each part, "
    "each label is one slot after its unit or part, keyed by that label."
)

FREE_TEXT_DEFINITION = (
    "The student writes a response the teacher judges using a sample answer, an analysis "
    "or grading guidance, rather than exact accepted strings for each response slot. "
    "Response length alone never makes a question free_text: a slot whose key lists the "
    "sentences it accepts is gap_fill."
)


def converter_kind_rule() -> str:
    """The converter prompt's kind rule for gap_fill and free_text, from the definitions."""
    return (
        "The gap_fill/free_text boundary is how the answer is scored. "
        f"gap_fill: {GAP_FILL_DEFINITION} "
        f"free_text: {FREE_TEXT_DEFINITION}"
    )


def labeler_boundary_sentences() -> str:
    """The labeler instruction's gap_fill/free_text sentences, from the definitions."""
    return (
        f"For gap_fill: {GAP_FILL_DEFINITION} "
        f"For free_text: {FREE_TEXT_DEFINITION} "
        "Response length alone does not distinguish these labels."
    )
