/**
 * Exam workspace gap word range.
 *
 * Domain purpose:
 *   The caret word the floating "Gör till lucka" button converts into a
 *   gap. A caret inside a word resolves to that word: a maximal run of word
 *   characters touching the caret on either side. A hyphen or an apostrophe
 *   (' or ') with word characters on both sides stays inside the word, so
 *   "Stockholms-läns" and "don't" convert as one gap seed; a trailing
 *   hyphen does not.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceRichTextEditor` for the floating gap button.
 */

const WORD_CHARACTER = /[\p{L}\p{M}\p{N}]/u;
const WORD_JOINER = new Set(["-", "'", "’"]);

function isWordCharacter(value: string | undefined): boolean {
  return value !== undefined && WORD_CHARACTER.test(value);
}

/**
 * The word at a caret offset into `text`, or null when neither neighbour is
 * a word character. Offsets are UTF-16 indices into `text`.
 */
export function wordRangeAt(text: string, offset: number): { from: number; to: number } | null {
  const before = offset > 0 ? text[offset - 1] : undefined;
  const at = offset < text.length ? text[offset] : undefined;
  if (!isWordCharacter(before) && !isWordCharacter(at)) {
    return null;
  }
  let from = offset;
  while (from > 0) {
    const current = text[from - 1];
    if (isWordCharacter(current)) {
      from -= 1;
      continue;
    }
    if (WORD_JOINER.has(current ?? "") && isWordCharacter(text[from - 2])) {
      from -= 1;
      continue;
    }
    break;
  }
  let to = offset;
  while (to < text.length) {
    const current = text[to];
    if (isWordCharacter(current)) {
      to += 1;
      continue;
    }
    if (WORD_JOINER.has(current ?? "") && isWordCharacter(text[to + 1])) {
      to += 1;
      continue;
    }
    break;
  }
  return { from, to };
}
