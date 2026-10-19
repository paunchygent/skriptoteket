/**
 * Exam workspace view labels.
 *
 * Domain purpose:
 *   Own the view's derived labels (TASK-SKRIPT-41-02-04): the list's
 *   instruction preview, the printed total, the course label, the formatted
 *   saved exports, and the zero-points flag.
 *
 * Relationships:
 *   - Consumed by `ExamWorkspaceView`, which binds the labels to the header,
 *     list, editor and drawers.
 */

import type { ComputedRef, Ref } from "vue";
import { computed } from "vue";

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspaceExports";
import { examWorkspaceSavedAt } from "./examWorkspaceFormat";
import { EXAM_WORKSPACE_EXPORT_FORMATS } from "./examWorkspaceExportFormats";
import { bodyText } from "./examWorkspaceRichText";
import { isEmptyBody } from "./examWorkspaceRichTextDocument";
import { examWorkspaceExamPrintedDifference } from "./examWorkspaceTotals";

export type ExamWorkspaceViewLabelsDeps = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  savedExports: Ref<Partial<Record<ExamWorkspaceExportTarget, string>>>;
  items: ComputedRef<NativeExamItem[]>;
};

export type ExamWorkspaceViewLabels = {
  examInstructionsPreview: ComputedRef<string | null>;
  examPrintedTotal: ComputedRef<number | null>;
  courseLabel: ComputedRef<string | null>;
  formattedSavedExports: ComputedRef<Partial<Record<ExamWorkspaceExportTarget, string>>>;
  zeroPoints: ComputedRef<boolean>;
};

export function useExamWorkspaceViewLabels(deps: ExamWorkspaceViewLabelsDeps): ExamWorkspaceViewLabels {
  /**
   * The list's "Instruktioner" preview: the text, or "Bild" for an instruction
   * of pictures without visible text; `null` for an instruction that prints nothing.
   */
  const examInstructionsPreview = computed(() => {
    const instructions = deps.workspaceDocument.value?.instructions ?? [];
    return isEmptyBody(instructions) ? null : bodyText(instructions) || "Bild";
  });
  const examPrintedTotal = computed(() =>
    deps.workspaceDocument.value ? examWorkspaceExamPrintedDifference(deps.workspaceDocument.value) : null,
  );
  const courseLabel = computed(() => deps.workspaceDocument.value?.header.course?.name ?? null);
  const formattedSavedExports = computed(() => {
    const formatted: Partial<Record<ExamWorkspaceExportTarget, string>> = {};
    for (const format of EXAM_WORKSPACE_EXPORT_FORMATS) {
      const iso = deps.savedExports.value[format.target];
      if (iso !== undefined) {
        formatted[format.target] = examWorkspaceSavedAt(iso);
      }
    }
    return formatted;
  });
  const zeroPoints = computed(() => deps.items.value.some((item) => item.points === 0));

  return {
    courseLabel,
    examInstructionsPreview,
    examPrintedTotal,
    formattedSavedExports,
    zeroPoints,
  };
}
