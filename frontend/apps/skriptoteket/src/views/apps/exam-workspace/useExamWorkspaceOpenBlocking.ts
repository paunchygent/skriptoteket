/**
 * Exam workspace open blocking.
 *
 * Domain purpose:
 *   One rule gating opening a saved exam: no open while busy, while the
 *   open exam has unsaved changes, or while the save status is not saved.
 *   One reason per blocked state feeds the hint, the entry tooltip and
 *   the blocked-click toast.
 *
 * Relationships:
 *   - Owned by `ExamWorkspaceOpenDrawer`, which passes its busy, dirty
 *     and save-status getters and reads `openBlocked` and `blockedReason`.
 *   - The pending-save copy is the shared save-status copy
 *     (`PENDING_SAVE_COPY`); the busy copy names only another operation,
 *     never the drawer's own import or conversion.
 */

import { computed } from "vue";
import type { ComputedRef } from "vue";

import { PENDING_SAVE_COPY } from "./useExamWorkspaceSaveStatus";

export type ExamWorkspaceOpenBlockingSaveState = "saving" | "saved" | "unsaved";

export type ExamWorkspaceOpenBlockingDeps = {
  /** True while any exam workspace operation runs. */
  isBusy: () => boolean;
  /** True while the open exam has edits not yet stored. */
  isDirty: () => boolean;
  /** The one save status: `saving` while an edit is not yet stored, `unsaved` when it reads Inte sparat. */
  saveState: () => ExamWorkspaceOpenBlockingSaveState;
  /** The save status's own reason while `saveState` is `unsaved`; null otherwise. */
  saveDetail: () => string | null;
  /**
   * True while an operation other than the drawer's own import or conversion
   * blocks opening; the busy hint names only this, never the drawer's own work.
   */
  isOpenBlockedByOtherOperation: () => boolean;
};

/** The busy reason: another operation blocks opening. */
export const OPEN_BUSY_COPY = "En annan åtgärd pågår. Försök igen om en stund.";

export function useExamWorkspaceOpenBlocking(deps: ExamWorkspaceOpenBlockingDeps): {
  openBlocked: ComputedRef<boolean>;
  blockedReason: ComputedRef<string | null>;
} {
  const openBlocked = computed(
    () => deps.isBusy() || deps.isDirty() || deps.saveState() !== "saved",
  );
  /** One reason per blocked state, used by the hint, the entry tooltip and the blocked-click toast. */
  const blockedReason = computed<string | null>(() => {
    if (deps.saveState() === "unsaved") {
      return deps.saveDetail() ?? PENDING_SAVE_COPY;
    }
    if (deps.saveState() === "saving" || deps.isDirty()) {
      return PENDING_SAVE_COPY;
    }
    if (deps.isOpenBlockedByOtherOperation()) {
      return OPEN_BUSY_COPY;
    }
    return null;
  });
  return { blockedReason, openBlocked };
}

/** A guest may start from a QTI .zip only; DigiExam (.dxe), Word (.docx) and PDF (.pdf) stay signed-in. */
export function isGuestImportFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".zip");
}
