/**
 * Exam workspace question-list notes.
 *
 * Domain purpose:
 *   The two derived note sources the question list shows: one entry per
 *   printed total that differs from its questions' sum, and, right after an
 *   import here, the questions whose points differ from the source's, in
 *   list order (TASK-SKRIPT-40-04-23); the latter is empty otherwise or
 *   after Avfärda. The list shows their lines and marks, the Poäng field
 *   the import hint.
 *
 * Relationships:
 *   - Called once by `ExamWorkspaceView` during setup; it provides the
 *     import-marked ids under `EXAM_WORKSPACE_IMPORT_POINTS_KEY` for the
 *     Poäng field and returns both sources for `ExamWorkspaceQuestionList`.
 *   - Whether the import check shows is `useExamWorkspaceImportPoints`;
 *     the rules are the pure `examWorkspaceImportPoints` and
 *     `examWorkspaceTotals`.
 */

import { computed, provide, type Ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { EXAM_WORKSPACE_IMPORT_POINTS_KEY, examWorkspaceImportPointsItemIds } from "./examWorkspaceImportPoints";
import { examWorkspacePrintedTotalMismatches } from "./examWorkspaceTotals";

export type ExamWorkspaceListNotesOptions = {
  /** The import-time check shows for the open exam. */
  importPointsShown: Readonly<Ref<boolean>>;
  /** The open exam, or null with none open. */
  document: Readonly<Ref<NativeExamDocument | null>>;
  /** The question list's item entries, in list order. */
  itemEntries: Readonly<Ref<readonly { id: string }[]>>;
};

export function useExamWorkspaceListNotes(options: ExamWorkspaceListNotesOptions) {
  const printedMismatches = computed(() =>
    options.document.value ? examWorkspacePrintedTotalMismatches(options.document.value) : [],
  );
  const importPointsIds = computed(() =>
    options.importPointsShown.value && options.document.value
      ? examWorkspaceImportPointsItemIds(
          options.itemEntries.value.map((entry) => entry.id),
          options.document.value.items,
        )
      : [],
  );
  provide(EXAM_WORKSPACE_IMPORT_POINTS_KEY, computed(() => new Set(importPointsIds.value)));
  return { importPointsIds, printedMismatches };
}
