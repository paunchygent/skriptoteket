/**
 * Exam workspace history cursor watcher (TASK-SKRIPT-40-04-14, KS2).
 *
 * Domain purpose:
 *   Consume the cursor the sync gate's fresh load installed, and drop the
 *   history's owed structural snapshots when the server replaced the copy the
 *   snapshots were owed from. Only the snapshots owed from the old copy no
 *   longer apply; the stored step list itself is reloaded by the gate's fresh
 *   load, which stands the editor on the fresh server copy.
 */

import { watch } from "vue";
import type { ComputedRef, Ref } from "vue";

import type { ExamWorkspaceHistoryDeps } from "./useExamWorkspaceHistory";

export type ExamWorkspaceHistoryCursorState = {
  /** Every stored step id, baseline first; a read echoing an older write is ignored. */
  ids: ComputedRef<string[]>;
  /** The cursor this tab last wrote; a read echoing an older cursor is ignored. */
  ownCursor: Ref<string | null>;
};

export function watchHistoryCursor(
  deps: Pick<ExamWorkspaceHistoryDeps, "historyCursor" | "lineageId" | "noteInstalledCursor">,
  state: ExamWorkspaceHistoryCursorState,
  reset: () => void,
  dropOwedSnapshots: () => void,
): void {
  watch(
    [() => deps.lineageId(), deps.historyCursor],
    ([lineageId, cursor], previous) => {
      const [previousLineage] = previous ?? [null, null];
      if (lineageId !== previousLineage) {
        // Another exam: drop the old list. The editing session starts the
        // gate's fresh load for the new lineage.
        reset();
        return;
      }
      if (!lineageId || !cursor) {
        return;
      }
      if (cursor === state.ownCursor.value) {
        return;
      }
      if (deps.noteInstalledCursor(lineageId, cursor)) {
        // The gate's own install: consume the event and change nothing. This
        // runs before the echo guard below, because the step list the gate
        // just read already contains the fresh cursor.
        return;
      }
      if (state.ownCursor.value !== null && state.ids.value.includes(cursor)) {
        // A read that started before this tab's last step write echoes an older cursor.
        deps.historyCursor.value = state.ownCursor.value;
        return;
      }
      // The server replaced the copy, so snapshots owed from the old copy no longer apply.
      dropOwedSnapshots();
    },
    { immediate: true },
  );
}
