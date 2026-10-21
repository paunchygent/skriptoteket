/**
 * Exam workspace import-time points check state (TASK-SKRIPT-40-04-23).
 *
 * Domain purpose:
 *   Whether the question list's import line and marks show. They show only
 *   right after an import started in this workspace: once its exam is open
 *   and no import or conversion runs any more. Opening any exam, the
 *   imported one included, ends the check, and so does Avfärda. The state
 *   lives only in memory, so a reload starts without it (P4).
 *
 * Relationships:
 *   - Built by `useExamWorkspaceDocument`: `useExamWorkspaceConversion`
 *     reports each import it starts, and every open reports its lineage.
 *   - Which questions differ is the pure `examWorkspaceImportPoints`.
 */

import { computed, ref, watch } from "vue";

export type ExamWorkspaceImportPointsOptions = {
  /** The open exam's lineage, or null with none open. */
  lineageId: () => string | null;
  /** No import or conversion runs: every converted question is in the open copy. */
  settled: () => boolean;
};

export function useExamWorkspaceImportPoints(options: ExamWorkspaceImportPointsOptions) {
  /** The lineage of an import started here whose exam has not settled open yet. */
  const pending = ref<string | null>(null);
  /** The lineage whose import settled open; the check shows while it stays open. */
  const fresh = ref<string | null>(null);

  watch(
    [pending, options.lineageId, options.settled],
    ([waiting, open, settled]) => {
      if (waiting !== null && waiting === open && settled) {
        fresh.value = waiting;
        pending.value = null;
      }
    },
    { immediate: true },
  );

  /** An import started here; its exam's lineage is known from the import's first answer. */
  function noteImportStarted(lineageId: string): void {
    pending.value = lineageId;
    fresh.value = null;
  }

  /** An exam is being opened: the check ends, and a pending import survives only its own open. */
  function noteOpening(lineageId: string): void {
    fresh.value = null;
    if (pending.value !== lineageId) {
      pending.value = null;
    }
  }

  /** Avfärda: hide the line and every mark for this import. */
  function dismiss(): void {
    fresh.value = null;
    pending.value = null;
  }

  const shown = computed(() => fresh.value !== null && fresh.value === options.lineageId());

  return { dismiss, noteImportStarted, noteOpening, shown };
}
