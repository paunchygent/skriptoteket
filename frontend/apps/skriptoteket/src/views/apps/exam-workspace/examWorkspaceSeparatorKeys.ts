/**
 * Exam workspace separator keyboard behavior.
 *
 * Domain purpose:
 *   The pure key-to-action mapping for one desktop resize handle, following
 *   the WAI-ARIA window-splitter pattern: arrows step, Home and End jump,
 *   Enter collapses and restores, Shift+Enter resets to the default width.
 *   ArrowRight widens the panel; the caller flips the direction for a panel
 *   on the right edge, so a right-edge handle passes mirrored arrows.
 *
 * Relationships:
 *   - Consumed by the later splitter wiring, which applies the returned
 *     action through `useExamWorkspaceColumnSizes` and reports the width
 *     through aria-valuenow, aria-valuemin and aria-valuemax.
 */

export type ExamWorkspaceSeparatorKeyInput = {
  key: string;
  shiftKey: boolean;
};

export type ExamWorkspaceSeparatorKeyBounds = {
  value: number;
  min: number;
  max: number;
};

export type ExamWorkspaceSeparatorKeyAction =
  | { kind: "set"; value: number }
  | { kind: "toggle-collapse" }
  | { kind: "reset" };

const ARROW_STEP_PX = 16;
const SHIFT_ARROW_STEP_PX = 64;

function clampWidth(value: number, bounds: ExamWorkspaceSeparatorKeyBounds): number {
  return Math.min(bounds.max, Math.max(bounds.min, value));
}

/**
 * Map one key press on a resize handle to its action. ArrowRight widens the
 * panel; mirror the arrows before calling for a panel on the right edge.
 * Returns null for keys the handle ignores.
 */
export function examWorkspaceSeparatorKeyAction(
  input: ExamWorkspaceSeparatorKeyInput,
  bounds: ExamWorkspaceSeparatorKeyBounds,
): ExamWorkspaceSeparatorKeyAction | null {
  const step = input.shiftKey ? SHIFT_ARROW_STEP_PX : ARROW_STEP_PX;
  switch (input.key) {
    case "ArrowLeft":
      return { kind: "set", value: clampWidth(bounds.value - step, bounds) };
    case "ArrowRight":
      return { kind: "set", value: clampWidth(bounds.value + step, bounds) };
    case "Home":
      return { kind: "set", value: bounds.min };
    case "End":
      return { kind: "set", value: bounds.max };
    case "Enter":
      return input.shiftKey ? { kind: "reset" } : { kind: "toggle-collapse" };
    default:
      return null;
  }
}
