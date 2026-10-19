/**
 * Exam workspace gap edits.
 *
 * Domain purpose:
 *   Each teacher edit the editor offers on one gap, as a pure transition from
 *   the item before the edit to the item after it, and the new gap a teacher
 *   adds. A teacher edit keys the item only while it still carries key data.
 *
 * Relationships:
 *   - Applied by `useExamWorkspaceItemEdits` and `useExamWorkspaceGapKeying`
 *     through their command paths.
 *   - Reads the teacher-key origin and the blank choices from
 *     `examWorkspaceItemEdits`, the one owner of both.
 *   - Kept-answer revert and restore live in `examWorkspaceKeptGapEdits`.
 */

import type {
  NativeExamBodyParagraph,
  NativeExamChoice,
  NativeExamGap,
  NativeExamItem,
  NativeExamItemKind,
} from "../../../api/examWorkspace";
import { teacherKeyOrigin } from "./examWorkspaceItemEdits";
import { plainBody } from "./examWorkspaceRichText";
import { placedGapIds } from "./examWorkspaceRichTextDocument";

/** The key value under the server's spelling policy: collapsed whitespace and folded case. */
function normalizedAnswer(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase("sv-SE");
}

/** Every accepted answer the question holds, in gap order and without duplicates. */
export function itemAcceptedAnswers(item: NativeExamItem): string[] {
  const seen = new Set<string>();
  const answers: string[] = [];
  for (const gap of item.gaps) {
    for (const value of gap.accepted_values) {
      if (!seen.has(value)) {
        seen.add(value);
        answers.push(value);
      }
    }
  }
  return answers;
}

/**
 * Append produced misspellings to one gap's automatic values, keeping the
 * existing ones: a value the question already accepts as a gold answer, one
 * the gap already carries, and one the teacher suppressed are all dropped
 * under the server's spelling policy (collapsed whitespace, folded case), and
 * the rest keep the producer's order and their display form.
 */
export function withAutomaticValues(
  item: NativeExamItem,
  gapId: string,
  values: string[],
): NativeExamItem {
  const gap = item.gaps.find((candidate) => candidate.gap_id === gapId);
  if (!gap || values.length === 0) {
    return item;
  }
  const known = new Set([
    ...itemAcceptedAnswers(item).map(normalizedAnswer),
    ...gap.automatic_values.map(normalizedAnswer),
    ...gap.excluded_automatic_values.map(normalizedAnswer),
  ]);
  const added: string[] = [];
  for (const value of values) {
    const normalized = normalizedAnswer(value);
    if (normalized.length > 0 && !known.has(normalized)) {
      known.add(normalized);
      added.push(value);
    }
  }
  if (added.length === 0) {
    return item;
  }
  return {
    ...item,
    gaps: item.gaps.map((candidate) =>
      candidate.gap_id === gapId
        ? { ...candidate, automatic_values: [...candidate.automatic_values, ...added] }
        : candidate,
    ),
  };
}

export function withGapValues(
  item: NativeExamItem,
  gapId: string,
  acceptedValues: string[],
): NativeExamItem {
  const current = item.gaps.find((gap) => gap.gap_id === gapId);
  if (
    !current ||
    (current.accepted_values.length === acceptedValues.length &&
      current.accepted_values.every((value, index) => value === acceptedValues[index]))
  ) {
    return item;
  }
  const gaps = item.gaps.map((gap) =>
    gap.gap_id === gapId ? { ...gap, accepted_values: acceptedValues } : gap,
  );
  const hasKeyData = gaps.some((gap) => gap.accepted_values.length > 0);
  return {
    ...item,
    answer_key: { ...item.answer_key, origin: teacherKeyOrigin(hasKeyData) },
    gaps,
  };
}

/** Replace one dropdown gap's options and its correct option; the same item when nothing changes. */
export function withGapOptions(
  item: NativeExamItem,
  gapId: string,
  options: NativeExamChoice[],
  correctOptionId: string | null,
): NativeExamItem {
  const current = item.gaps.find((gap) => gap.gap_id === gapId);
  if (
    !current ||
    (current.correct_option_id === correctOptionId &&
      current.options.length === options.length &&
      current.options.every((option, index) => option === options[index]))
  ) {
    return item;
  }
  const gaps = item.gaps.map((gap) =>
    gap.gap_id === gapId ? { ...gap, options, correct_option_id: correctOptionId } : gap,
  );
  // Only a changed correct option is the teacher's decision; a text, add,
  // remove or reorder edit leaves an AI or machine-proposed key unapproved.
  if (current.correct_option_id === correctOptionId) {
    return { ...item, gaps };
  }
  const hasKeyData = gaps.some((gap) => gap.correct_option_id !== null);
  return {
    ...item,
    answer_key: { ...item.answer_key, origin: teacherKeyOrigin(hasKeyData) },
    gaps,
  };
}

/**
 * Remove only the selected automatic answer, preserving the key's
 * provenance, and suppress it so no later reply or regeneration adds it back.
 */
export function withoutAutomaticValue(
  item: NativeExamItem,
  gapId: string,
  value: string,
): NativeExamItem {
  const gap = item.gaps.find((candidate) => candidate.gap_id === gapId);
  const normalized = normalizedAnswer(value);
  if (
    !gap ||
    normalized.length === 0 ||
    !gap.automatic_values.some((entry) => normalizedAnswer(entry) === normalized)
  ) {
    return item;
  }
  const suppressed = gap.excluded_automatic_values.some(
    (entry) => normalizedAnswer(entry) === normalized,
  );
  return {
    ...item,
    gaps: item.gaps.map((candidate) =>
      candidate.gap_id === gapId
        ? {
            ...candidate,
            automatic_values: candidate.automatic_values.filter(
              (entry) => normalizedAnswer(entry) !== normalized,
            ),
            excluded_automatic_values: suppressed
              ? candidate.excluded_automatic_values
              : [...candidate.excluded_automatic_values, value],
          }
        : candidate,
    ),
  };
}

/** Replace a gap with its first accepted answer as plain text; a gap without an answer stays. */
export function withGapAsText(item: NativeExamItem, gapId: string): NativeExamItem {
  const gap = item.gaps.find((candidate) => candidate.gap_id === gapId);
  const text = gap?.accepted_values[0];
  if (!text) {
    return item;
  }
  return {
    ...item,
    gaps: item.gaps.filter((candidate) => candidate.gap_id !== gapId),
    body: item.body.map((paragraph) => ({
      ...paragraph,
      segments: paragraph.segments.map((segment) =>
        segment.kind === "gap" && segment.gap_id === gapId
          ? { kind: "text" as const, text, marks: [], kept_gap_id: null }
          : segment,
      ),
    })),
  };
}

const GAP_ID_PATTERN = /^gap_([0-9]{3})$/;
const MAX_GAP_NUMBER = 999;

/**
 * The next free gap id above the item's highest declared or placed gap, as
 * `gap_NNN`; `gap_001` when there are none, null when the next number would
 * exceed 999. Ids outside the `gap_NNN` shape never count.
 */
export function nextGapId(item: NativeExamItem): string | null {
  let highest = 0;
  const candidates = [...item.gaps.map((gap) => gap.gap_id), ...placedGapIds(item.body)];
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
 * The gap record one creation seeds: a Lucktext gap carries the converted
 * text as its accepted value, a dropdown gap carries it as its one correct
 * option, and an empty insertion carries a blank gap of the item's kind: a
 * Lucktext gap with no accepted values, a dropdown gap with no options and
 * no correct option, so the teacher adds the first option in the popover.
 */
function newGapRecord(kind: NativeExamItemKind, gapId: string, seed: string): NativeExamGap {
  const text = seed.trim();
  if (kind === "inline_choice") {
    if (text.length === 0) {
      return {
        accepted_values: [],
        automatic_values: [],
        correct_option_id: null,
        excluded_automatic_values: [],
        gap_id: gapId,
        options: [],
      };
    }
    return {
      accepted_values: [],
      automatic_values: [],
      correct_option_id: "choice_001",
      excluded_automatic_values: [],
      gap_id: gapId,
      options: [{ body: plainBody(text), choice_id: "choice_001" }],
    };
  }
  return {
    accepted_values: text.length > 0 ? [text] : [],
    automatic_values: [],
    correct_option_id: null,
    excluded_automatic_values: [],
    gap_id: gapId,
    options: [],
  };
}

/**
 * Create one gap as one atomic structural item edit: the passed body plus the
 * new gap record together, mirroring `withGapAsText`. Kept records follow the
 * new body's placement order, so the gap's number follows the text; records
 * the new body no longer places leave with it. Anything but exactly one
 * placement of a new gap on a Lucktext or dropdown question returns the same
 * item. The written body is the passed body, so the editor's echo guard sees
 * JSON-equal content.
 *
 * The new record's key data keys the item through `teacherKeyOrigin`,
 * computed over all gaps as `withGapValues` and `withGapOptions` do; a
 * keyless insertion into a keyless item keeps the absent origin. An empty
 * insertion that adds no key data of its own leaves the answer key exactly
 * as it is, so it never silently approves an AI or machine-proposed key.
 * Only a new record with a non-empty accepted list or a set correct option
 * re-keys the item; an empty dropdown gap carries neither, so a Tom lucka
 * insertion never keys the item.
 */
export function withNewGap(
  item: NativeExamItem,
  body: NativeExamBodyParagraph[],
  gapId: string,
  seed: string,
): NativeExamItem {
  if (item.kind !== "gap_fill" && item.kind !== "inline_choice") {
    return item;
  }
  if (item.gaps.some((gap) => gap.gap_id === gapId)) {
    return item;
  }
  const placed = placedGapIds(body);
  if (placed.filter((placedId) => placedId === gapId).length !== 1) {
    return item;
  }
  const order = new Map(placed.map((placedId, index) => [placedId, index]));
  const position = order.get(gapId) ?? placed.length;
  const kept = item.gaps.filter((gap) => order.has(gap.gap_id));
  const record = newGapRecord(item.kind, gapId, seed);
  const insertAt = kept.findIndex((gap) => (order.get(gap.gap_id) ?? placed.length) > position);
  const gaps = [...kept];
  if (insertAt < 0) {
    gaps.push(record);
  } else {
    gaps.splice(insertAt, 0, record);
  }
  const recordHasKeyData =
    record.accepted_values.length > 0 || record.correct_option_id !== null;
  if (!recordHasKeyData) {
    return { ...item, body, gaps };
  }
  const hasKeyData = gaps.some(
    (gap) => gap.accepted_values.length > 0 || gap.correct_option_id !== null,
  );
  return {
    ...item,
    answer_key: { ...item.answer_key, origin: teacherKeyOrigin(hasKeyData) },
    body,
    gaps,
  };
}

/**
 * Whether the gap holds an answer: a Lucktext gap with at least one accepted
 * value, a dropdown gap whose correct option names one of its declared
 * options. This mirrors the export refusal (`partial_gap_key` for Lucktext,
 * `gap_without_correct_option` for dropdowns) and the readiness rules
 * (`isPartiallyKeyedGapItem`, `dropdownGapsWithoutCorrectOption`) instead of
 * restating them: an empty accepted list, a missing correct option or no
 * declared options is the unanswered gap.
 */
export function gapHasAnswer(gap: NativeExamGap | undefined, kind: NativeExamItemKind): boolean {
  if (!gap) {
    return false;
  }
  if (kind === "inline_choice") {
    return (
      gap.correct_option_id !== null &&
      gap.options.some((option) => option.choice_id === gap.correct_option_id)
    );
  }
  return gap.accepted_values.length > 0;
}

/**
 * The body with one gap's placement removed; the other segments keep their
 * order, and an emptied paragraph keeps no segments, as `bodyFromEditor`
 * writes one. The owner drops the gap's record through `withBody`, so
 * emitting this body as one structural edit removes the gap in one undo step.
 */
export function bodyWithoutGap(
  body: readonly NativeExamBodyParagraph[],
  gapId: string,
): NativeExamBodyParagraph[] {
  return body.map((paragraph) => ({
    ...paragraph,
    segments: paragraph.segments.filter(
      (segment) => !(segment.kind === "gap" && segment.gap_id === gapId),
    ),
  }));
}
