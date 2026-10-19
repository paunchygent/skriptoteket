/**
 * Exam workspace gap word range.
 *
 * Domain purpose:
 *   The caret word the floating "Lucka" button ("Gör till lucka" tooltip and
 *   accessible name) converts into a gap. A caret inside a word resolves to
 *   that word: a maximal run of word characters touching the caret on either
 *   side. A hyphen or an apostrophe (' or ') with word characters on both
 *   sides stays inside the word, so "Stockholms-läns" and "don't" convert as
 *   one gap seed; a trailing hyphen does not.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceMakeGap` for the caret word and the floating
 *     button word, resolved over the whole textblock in document positions.
 */

import type { Node as ProseMirrorNode } from "@tiptap/pm/model";

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

/**
 * An inline atom as one non-word character: gaps, pictures and hard breaks
 * each have node size one, so one placeholder per leaf keeps the flat text
 * aligned with the textblock's parent offsets.
 */
const ATOM_PLACEHOLDER = "￼";

/**
 * The word at a document position, as document positions, or null when the
 * position is not inside a word. The textblock's text is read whole, across
 * adjacent differently marked text nodes, with one placeholder per inline
 * atom, so a word split across marks resolves as one word and a word stops
 * at real separators and at inline atoms.
 */
export function wordRangeAtDocPosition(
  doc: ProseMirrorNode,
  pos: number,
): { from: number; to: number } | null {
  if (pos < 0 || pos > doc.content.size) {
    return null;
  }
  const resolved = doc.resolve(pos);
  const parent = resolved.parent;
  if (!parent.isTextblock) {
    return null;
  }
  const blockStart = resolved.pos - resolved.parentOffset;
  const flat = parent.textBetween(0, parent.content.size, undefined, ATOM_PLACEHOLDER);
  const range = wordRangeAt(flat, resolved.parentOffset);
  if (range === null) {
    return null;
  }
  return { from: blockStart + range.from, to: blockStart + range.to };
}
