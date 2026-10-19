/**
 * Exam workspace shared rich-text toolbar wiring.
 *
 * Domain purpose:
 *   The one place that reads the registry's active rich target for a mark
 *   toolbar: its pressed marks and heading level, dispatching mark and
 *   heading toggles to that target. The question text and the Kort svar
 *   Fråga field share it, so a glyph action always edits the surface that
 *   owns the selection, never a stale one.
 *
 * Relationships:
 *   - Consumed by `ExamWorkspaceBodyEditor` (which also keeps the registry's
 *     active target for its Lucka command) and
 *     `ExamWorkspaceShortAnswerField`.
 *   - Reads the registry from `examWorkspaceRichTextTarget`, provided once
 *     per item editor (`ExamWorkspaceQuestionEditor`).
 */

import { computed } from "vue";
import type { ComputedRef, Ref } from "vue";

import type { BodyMark } from "./examWorkspaceBodyMarks";
import { useRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextHeadingLevel, RichTextTarget } from "./examWorkspaceRichTextTarget";

export function useExamWorkspaceRichTextToolbar(): {
  activeRichTextTarget: Ref<RichTextTarget | null>;
  activeMarks: ComputedRef<BodyMark[]>;
  activeHeading: ComputedRef<RichTextHeadingLevel | null>;
  toggleMark: (mark: BodyMark) => void;
  toggleHeading: (level: RichTextHeadingLevel) => void;
} {
  const richTextTargets = useRichTextTargetRegistry();
  const activeRichTextTarget = richTextTargets.active;
  const activeMarks = computed(() => activeRichTextTarget.value?.marks.value ?? []);
  const activeHeading = computed(() => activeRichTextTarget.value?.headingLevel() ?? null);

  function toggleMark(mark: BodyMark): void {
    activeRichTextTarget.value?.toggleMark(mark);
  }

  function toggleHeading(level: RichTextHeadingLevel): void {
    activeRichTextTarget.value?.toggleHeading(level);
  }

  return { activeRichTextTarget, activeMarks, activeHeading, toggleMark, toggleHeading };
}
