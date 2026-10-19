/**
 * Exam workspace gap word range.
 *
 * Domain purpose:
 *   The caret word the floating "Lucka" button ("Gör till lucka" tooltip and
 *   accessible name) converts into a gap. A caret inside a word resolves to
 *   that word: a maximal run of word characters touching the caret on either
 *   side. A hyphen or an apostrophe (' or ') with word characters on both
 *   sides stays inside the word, so "Stockholms-läns" and "don't" convert as
 *   one gap seed; a trailing hyphen does not. The gap tool's click path
 *   resolves instead the word containing the pointer-hit character, so a
 *   click on a space or punctuation only places the caret.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceMakeGap` for the caret word and the floating
 *     button word, resolved over the whole textblock in document positions,
 *     and for the pointer-hit word on the gap tool click path.
 */

import type { Node as ProseMirrorNode } from "@tiptap/pm/model";

const WORD_CHARACTER = /[\p{L}\p{M}\p{N}]/u;
const WORD_JOINER = new Set(["-", "'", "’"]);

function isWordCharacter(value: string | undefined): boolean {
  return value !== undefined && WORD_CHARACTER.test(value);
}

/**
 * Expand `from`..`to` to the maximal word around it: a run of word
 * characters, where a hyphen or an apostrophe (' or ') with word characters
 * on both sides stays inside. Offsets are UTF-16 indices into `text`.
 */
function expandWord(text: string, from: number, to: number): { from: number; to: number } {
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
 * The word at a caret offset into `text`, or null when neither neighbour is
 * a word character. Offsets are UTF-16 indices into `text`.
 */
export function wordRangeAt(text: string, offset: number): { from: number; to: number } | null {
  const before = offset > 0 ? text[offset - 1] : undefined;
  const at = offset < text.length ? text[offset] : undefined;
  if (!isWordCharacter(before) && !isWordCharacter(at)) {
    return null;
  }
  return expandWord(text, offset, offset);
}

/**
 * The word containing the character at `index` into `text`, or null when
 * that character is not a word character. A hyphen or an apostrophe (' or
 * ') with word characters on both sides counts as inside the word, so it
 * resolves like any other word character; any other separator, and any
 * character outside `text`, resolves to nothing. Offsets are UTF-16 indices
 * into `text`.
 */
export function wordRangeAtCharacter(text: string, index: number): { from: number; to: number } | null {
  if (index < 0 || index >= text.length) {
    return null;
  }
  const hit = text[index];
  if (isWordCharacter(hit)) {
    return expandWord(text, index, index + 1);
  }
  if (
    WORD_JOINER.has(hit ?? "") &&
    isWordCharacter(index > 0 ? text[index - 1] : undefined) &&
    isWordCharacter(index + 1 < text.length ? text[index + 1] : undefined)
  ) {
    return expandWord(text, index, index + 1);
  }
  return null;
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

/**
 * The word containing the character starting at document position `charPos`,
 * as document positions, or null when that character is not a word
 * character. The character maps onto the same whole-textblock flat text as
 * `wordRangeAtDocPosition` (one placeholder per inline atom), so a word
 * split across marks resolves as one word and a separator or an atom stops
 * it. A position outside any character resolves to nothing.
 */
export function wordRangeAtDocCharacter(
  doc: ProseMirrorNode,
  charPos: number,
): { from: number; to: number } | null {
  if (charPos < 0 || charPos >= doc.content.size) {
    return null;
  }
  const resolved = doc.resolve(charPos);
  const parent = resolved.parent;
  if (!parent.isTextblock) {
    return null;
  }
  const blockStart = resolved.pos - resolved.parentOffset;
  const flat = parent.textBetween(0, parent.content.size, undefined, ATOM_PLACEHOLDER);
  const range = wordRangeAtCharacter(flat, resolved.parentOffset);
  if (range === null) {
    return null;
  }
  return { from: blockStart + range.from, to: blockStart + range.to };
}
