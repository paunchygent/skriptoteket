/**
 * Exam workspace gap labels.
 *
 * Domain purpose:
 *   How a gap reads to the teacher: its accepted answers, or "Lucka N" by its
 *   declared position while it has none, and the comma-separated input the
 *   gap popover turns into accepted answers.
 *
 * Relationships:
 *   - `ExamWorkspaceBodyEditor` draws gaps in the question text from
 *     `gapNumberIn` and `examGapStates`.
 *   - `ExamWorkspaceGapPopover` reads typed answers through `parseAcceptedValues`.
 */

import type { NativeExamGap } from "../../../api/examWorkspace";
import type { ExamGapState } from "./examWorkspaceRichTextSchema";

/** A gap's 1-based declared position, or 0 when the item does not declare it. */
export function gapNumberIn(gaps: readonly NativeExamGap[], gapId: string): number {
  return gaps.findIndex((gap) => gap.gap_id === gapId) + 1;
}

/** The gap's accepted answers joined, or "Lucka N" while it has none. */
export function gapChipLabel(gap: NativeExamGap | undefined, gapNumber: number): string {
  if (gap && gap.accepted_values.length > 0) {
    return gap.accepted_values.join(" / ");
  }
  return gapNumber > 0 ? `Lucka ${gapNumber}` : "Lucka";
}

/** How each declared gap is drawn in the text, keyed by gap id. */
export function examGapStates(gaps: readonly NativeExamGap[]): Record<string, ExamGapState> {
  return Object.fromEntries(
    gaps.map((gap, index) => {
      const label = gapChipLabel(gap, index + 1);
      const empty = gap.accepted_values.length === 0;
      const accessibleLabel = empty
        ? `Lucka ${index + 1}, saknar godkända svar`
        : `Lucka ${index + 1}, godkända svar: ${label}`;
      return [gap.gap_id, { label, accessibleLabel, empty }];
    }),
  );
}

/** Comma-separated input → accepted values: split, trim, drop empty. */
export function parseAcceptedValues(raw: string): string[] {
  return raw
    .split(",")
    .map((value) => value.trim())
    .filter((value) => value.length > 0);
}
