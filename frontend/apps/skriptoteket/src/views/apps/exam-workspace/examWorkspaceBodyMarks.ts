/**
 * Exam workspace rich-text marks.
 *
 * Domain purpose:
 *   The five marks the native document keeps (bold, italic, underline,
 *   superscript, subscript) and their Swedish action names. Superscript and
 *   subscript exclude each other in the editor schema, because one glyph
 *   cannot sit both above and below the baseline.
 *
 * Relationships:
 *   - `examWorkspaceRichTextDocument` maps these marks to and from editor marks.
 *   - `ExamWorkspaceMarkToolbar` takes its buttons and glyph labels from here.
 */

/** Every mark the native document stores, in the order a toolbar shows them. */
export const BODY_MARKS = ["bold", "italic", "underline", "superscript", "subscript"] as const;

export type BodyMark = (typeof BODY_MARKS)[number];

/** The Swedish action name for a mark button's tooltip and accessible name. */
export const MARK_LABELS: Record<BodyMark, string> = {
  bold: "Fet",
  italic: "Kursiv",
  underline: "Understruken",
  superscript: "Upphöjd",
  subscript: "Nedsänkt",
};
