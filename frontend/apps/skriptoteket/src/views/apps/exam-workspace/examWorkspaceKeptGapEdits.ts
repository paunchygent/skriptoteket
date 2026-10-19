/**
 * Exam workspace kept-gap edits.
 *
 * Domain purpose:
 *   The teacher's revert and restore of one gap's kept answers, as pure
 *   transitions from the item before the edit to the item after it. Reverting
 *   turns a gap's placement into a word that keeps the gap's record hidden;
 *   restoring turns the whole kept word back into the gap, with the word's
 *   current text as the first answer.
 *
 * Relationships:
 *   - Applied by `useExamWorkspaceItemEdits` through its revert and restore
 *     commands.
 *   - Reuses `withGapAsText` from `examWorkspaceGapEdits` for the text part
 *     of a revert, and the gap id scans from
 *     `examWorkspaceRichTextDocument`.
 */

import type {
  NativeExamBodyParagraph,
  NativeExamBodySegment,
  NativeExamGap,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { withGapAsText } from "./examWorkspaceGapEdits";
import { bodyText, plainBody } from "./examWorkspaceRichText";
import { placedGapIds, placedKeptGapIds } from "./examWorkspaceRichTextDocument";

const GAP_ID_PATTERN = /^gap_([0-9]{3})$/;
const MAX_GAP_NUMBER = 999;

/**
 * The next free kept gap id above the item's highest declared, kept or
 * placed gap id, as `gap_NNN`; `gap_001` when there are none, null when the
 * next number would exceed 999. Kept ids share the gap number space and the
 * `gap_NNN` shape, following `nextGapId`, so one scan keeps them unique and
 * apart from the item's gaps, kept gaps and chips.
 */
export function nextKeptGapId(item: NativeExamItem): string | null {
  let highest = 0;
  const candidates = [
    ...item.gaps.map((gap) => gap.gap_id),
    ...item.kept_gaps.map((gap) => gap.gap_id),
    ...placedGapIds(item.body),
    ...placedKeptGapIds(item.body),
  ];
  for (const candidate of candidates) {
    const match = GAP_ID_PATTERN.exec(candidate);
    if (match) {
      highest = Math.max(highest, Number(match[1]));
    }
  }
  if (highest >= MAX_GAP_NUMBER) {
    return null;
  }
  return `gap_${String(highest + 1).padStart(3, "0")}`;
}

/**
 * Revert one gap to its word: the gap's placement becomes a text run holding
 * the gap's first accepted answer (Lucktext) or its correct option's text
 * (dropdown), linked by a new kept id from `nextKeptGapId`, and the gap's
 * full record moves into `kept_gaps` under that id while the gap leaves
 * `gaps`. The kept record keeps every answer, automatic value and option, so
 * the word's text duplicates the head answer and an unedited restore is
 * exact; the text part reuses `withGapAsText` on the gap (Lucktext) or on the
 * gap seeded with the correct option's text (dropdown). A gap without an
 * answer, without a body placement, or with no free kept id stays.
 */
export function withGapReverted(item: NativeExamItem, gapId: string): NativeExamItem {
  if (item.kind !== "gap_fill" && item.kind !== "inline_choice") {
    return item;
  }
  const gap = item.gaps.find((candidate) => candidate.gap_id === gapId);
  if (!gap) {
    return item;
  }
  const keptGapId = nextKeptGapId(item);
  if (keptGapId === null) {
    return item;
  }
  let placementParagraph = -1;
  let placementSegment = -1;
  item.body.forEach((paragraph, paragraphIndex) => {
    paragraph.segments.forEach((segment, segmentIndex) => {
      if (segment.kind === "gap" && segment.gap_id === gapId) {
        placementParagraph = paragraphIndex;
        placementSegment = segmentIndex;
      }
    });
  });
  if (placementParagraph < 0 || placementSegment < 0) {
    return item;
  }
  if (item.kind === "gap_fill") {
    if (!gap.accepted_values[0]) {
      return item;
    }
    return linkRevertedWord(withGapAsText(item, gapId), gap, keptGapId, placementParagraph, placementSegment);
  }
  const correct = gap.options.find((option) => option.choice_id === gap.correct_option_id);
  const text = correct ? bodyText(correct.body) : "";
  if (text.length === 0) {
    return item;
  }
  const seeded: NativeExamItem = {
    ...item,
    gaps: item.gaps.map((candidate) =>
      candidate.gap_id === gapId ? { ...candidate, accepted_values: [text] } : candidate,
    ),
  };
  return linkRevertedWord(withGapAsText(seeded, gapId), gap, keptGapId, placementParagraph, placementSegment);
}

/** Attach the kept id to the reverted word and keep the gap's full record under it. */
function linkRevertedWord(
  item: NativeExamItem,
  gap: NativeExamGap,
  keptGapId: string,
  placementParagraph: number,
  placementSegment: number,
): NativeExamItem {
  return {
    ...item,
    body: item.body.map((paragraph, paragraphIndex) =>
      paragraphIndex === placementParagraph
        ? {
            ...paragraph,
            segments: paragraph.segments.map((segment, segmentIndex) =>
              segmentIndex === placementSegment && segment.kind === "text"
                ? { ...segment, kept_gap_id: keptGapId }
                : segment,
            ),
          }
        : paragraph,
    ),
    kept_gaps: [...item.kept_gaps, { ...gap, gap_id: keptGapId }],
  };
}

/**
 * Restore one kept word to its gap: the kept block the teacher clicked
 * becomes one gap placement, and the kept record becomes the gap again under
 * the same id. `atBlock` names the contiguous kept block in body order
 * (0-based; out of range throws naming the id and the block), so a click on
 * the second block of a split id restores that block instead of the first
 * one. The
 * word's current text becomes the first accepted answer (Lucktext) or the
 * correct option's text (dropdown), and the kept answers and options come
 * back, so an unedited word restores the gap exactly apart from the gap id,
 * which changed when the gap was reverted. A word split by formatting
 * restores as one gap from the joined text; the other kept runs lose the
 * link and stay plain text. An unknown kept id, a kept record no run names,
 * an empty word, or a kept dropdown record with no correct option stays.
 */
export function withKeptGapRestored(
  item: NativeExamItem,
  keptGapId: string,
  atBlock: number,
): NativeExamItem {
  if (item.kind !== "gap_fill" && item.kind !== "inline_choice") {
    return item;
  }
  const kept = item.kept_gaps.find((candidate) => candidate.gap_id === keptGapId);
  if (!kept) {
    return item;
  }
  type KeptBlock = { paragraph: number; start: number; end: number };
  const blocks: KeptBlock[] = [];
  item.body.forEach((paragraph, paragraphIndex) => {
    let start = -1;
    paragraph.segments.forEach((segment, segmentIndex) => {
      const linked = segment.kind === "text" && segment.kept_gap_id === keptGapId;
      if (linked && start < 0) {
        start = segmentIndex;
      }
      if (!linked && start >= 0) {
        blocks.push({ paragraph: paragraphIndex, start, end: segmentIndex });
        start = -1;
      }
    });
    if (start >= 0) {
      blocks.push({ paragraph: paragraphIndex, start, end: paragraph.segments.length });
    }
  });
  if (blocks.length === 0) {
    return item;
  }
  const picked = blocks[atBlock];
  if (!picked) {
    throw new Error(`cannot restore kept gap ${keptGapId}: block ${atBlock} is out of range`);
  }
  const blockParagraph = picked.paragraph;
  const blockStart = picked.start;
  const blockEnd = picked.end;
  const block = item.body[blockParagraph]?.segments.slice(blockStart, blockEnd) ?? [];
  const word = block
    .map((segment) => (segment.kind === "text" ? segment.text : ""))
    .join("");
  if (word.length === 0) {
    return item;
  }
  let record: NativeExamGap;
  if (item.kind === "gap_fill") {
    record = { ...kept, gap_id: keptGapId, accepted_values: [word, ...kept.accepted_values.slice(1)] };
  } else {
    const correct = kept.options.find((option) => option.choice_id === kept.correct_option_id);
    if (!correct) {
      return item;
    }
    record = {
      ...kept,
      gap_id: keptGapId,
      options: kept.options.map((option) =>
        option.choice_id === kept.correct_option_id && bodyText(option.body) !== word
          ? { ...option, body: plainBody(word) }
          : option,
      ),
    };
  }
  const body = item.body.map((paragraph, paragraphIndex) => {
    if (paragraphIndex !== blockParagraph) {
      return withoutKeptLink(paragraph, keptGapId);
    }
    const segments: NativeExamBodySegment[] = [];
    paragraph.segments.forEach((segment, segmentIndex) => {
      if (segmentIndex === blockStart) {
        segments.push({ gap_id: keptGapId, kind: "gap" });
      }
      if (segmentIndex >= blockStart && segmentIndex < blockEnd) {
        return;
      }
      segments.push(
        segment.kind === "text" && segment.kept_gap_id === keptGapId
          ? { ...segment, kept_gap_id: null }
          : segment,
      );
    });
    return { ...paragraph, segments };
  });
  const order = new Map(placedGapIds(body).map((placedId, index) => [placedId, index]));
  const gaps = [...item.gaps, record].sort(
    (left, right) => (order.get(left.gap_id) ?? 0) - (order.get(right.gap_id) ?? 0),
  );
  return {
    ...item,
    body,
    gaps,
    kept_gaps: item.kept_gaps.filter((candidate) => candidate.gap_id !== keptGapId),
  };
}

/** The paragraph with a kept id stripped from every run; the text stays plain. */
function withoutKeptLink(
  paragraph: NativeExamBodyParagraph,
  keptGapId: string,
): NativeExamBodyParagraph {
  return {
    ...paragraph,
    segments: paragraph.segments.map((segment) =>
      segment.kind === "text" && segment.kept_gap_id === keptGapId
        ? { ...segment, kept_gap_id: null }
        : segment,
    ),
  };
}
