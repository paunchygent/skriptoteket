/**
 * Exam workspace gap labels.
 *
 * Domain purpose:
 *   How a gap reads to the teacher: a Lucktext gap shows its accepted
 *   answers, a dropdown gap its correct option's text, or "Lucka N" by its
 *   declared position while it has none. The screen-reader label names the
 *   dropdown's options state instead of accepted values.
 *
 * Relationships:
 *   - `ExamWorkspaceBodyEditor` draws gaps in the question text from
 *     `gapNumberIn` and `examGapStates`.
 */

import type { NativeExamGap, NativeExamItemKind } from "../../../api/examWorkspace";
import type { ExamGapState } from "./examWorkspaceRichTextSchema";
import { gapHasAnswer } from "./examWorkspaceGapEdits";
import { bodyText } from "./examWorkspaceRichText";

/** A gap's 1-based declared position, or 0 when the item does not declare it. */
export function gapNumberIn(gaps: readonly NativeExamGap[], gapId: string): number {
  return gaps.findIndex((gap) => gap.gap_id === gapId) + 1;
}

/** The correct option's plain text, or "" when the gap names no declared option. */
function correctOptionText(gap: NativeExamGap | undefined): string {
  const correct = gap?.options.find((option) => option.choice_id === gap.correct_option_id);
  return correct ? bodyText(correct.body) : "";
}

/** The gap's accepted answers (Lucktext) or correct option (dropdown), or "Lucka N" while it has none. */
export function gapChipLabel(
  gap: NativeExamGap | undefined,
  gapNumber: number,
  kind: NativeExamItemKind,
): string {
  if (kind === "inline_choice") {
    const text = correctOptionText(gap);
    if (text.length > 0) {
      return text;
    }
    return gapNumber > 0 ? `Lucka ${gapNumber}` : "Lucka";
  }
  if (gap && gap.accepted_values.length > 0) {
    return gap.accepted_values.join(" / ");
  }
  return gapNumber > 0 ? `Lucka ${gapNumber}` : "Lucka";
}

/** How each declared gap is drawn in the text, keyed by gap id. */
export function examGapStates(
  gaps: readonly NativeExamGap[],
  kind: NativeExamItemKind,
): Record<string, ExamGapState> {
  return Object.fromEntries(
    gaps.map((gap, index) => {
      const number = index + 1;
      if (kind === "inline_choice") {
        const label = gapChipLabel(gap, number, kind);
        const empty = !gapHasAnswer(gap, kind);
        const options = gap.options.map((option) => bodyText(option.body));
        const correct = correctOptionText(gap);
        let accessibleLabel: string;
        if (options.length === 0) {
          accessibleLabel = `Lucka ${number}, rullista utan alternativ`;
        } else if (correct.length > 0) {
          accessibleLabel = `Lucka ${number}, rullista med alternativen ${options.join(", ")}, rätt alternativ: ${correct}`;
        } else {
          accessibleLabel = `Lucka ${number}, rullista med alternativen ${options.join(", ")}, saknar rätt alternativ`;
        }
        return [gap.gap_id, { label, accessibleLabel, empty }];
      }
      const label = gapChipLabel(gap, number, kind);
      const empty = gap.accepted_values.length === 0;
      const accessibleLabel = empty
        ? `Lucka ${number}, saknar godkända svar`
        : `Lucka ${number}, godkända svar: ${label}`;
      return [gap.gap_id, { label, accessibleLabel, empty }];
    }),
  );
}
