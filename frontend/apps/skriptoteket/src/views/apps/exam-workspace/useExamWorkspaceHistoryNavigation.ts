/**
 * Exam workspace undo and redo through the server position.
 *
 * Domain purpose:
 *   Ångra and Gör om move between stored steps through the position move,
 *   which writes that step's document to the exam file without storing a new
 *   step, so the server position and the file follow the teacher; a new edit
 *   after an undo drops the redo steps. Undo first stores any pending edit,
 *   so the pending edit itself can be redone; a 409 from the move reloads
 *   the server copy through `onConflict`, which replaces the pending edit,
 *   and undo stops. A 422 from the move means the step changes a placeholder
 *   still being converted: undo stops and the status shows Inte sparat with
 *   the guard's reason.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceHistory`, which owns the step list, the
 *     cursor and the flush the navigation runs first. The navigation reports
 *     every confirmed move through the save status, so the status and the
 *     saved baseline follow undo and redo too.
 */

import type { ComputedRef, Ref } from "vue";

import { isApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { isEditLeaseHeldError } from "./useExamWorkspaceEditLease";
import type { FenceToken } from "./examWorkspaceSyncFence";
import { refusalReason, type StoreOutcome } from "./useExamWorkspaceSaveStatus";
import type { ExamWorkspaceHistoryDeps } from "./useExamWorkspaceHistory";

const UNDO_FAILURE_COPY = "Det gick inte att ångra. Försök igen.";
const REDO_FAILURE_COPY = "Det gick inte att göra om. Försök igen.";

export type ExamWorkspaceHistoryNavigationDeps = {
  /** The installed step list, newest last; the baseline is not included. */
  baselineId: Ref<string | null>;
  stepIds: Ref<string[]>;
  /** The stored snapshot the editor stands on; null until the step list is loaded. */
  position: Ref<string | null>;
  /** That step's document; a working copy that differs from it is a pending edit. */
  stepDocument: Ref<NativeExamDocument | null>;
  /** The cursor this tab last wrote; a read echoing an older cursor is ignored. */
  ownCursor: Ref<string | null>;
  /** True while an undo or redo move is running. */
  navigating: Ref<boolean>;
  canUndo: ComputedRef<boolean>;
  canRedo: ComputedRef<boolean>;
  /** The step ids with the baseline first, and the standing step's index in it. */
  ids: ComputedRef<string[]>;
  index: ComputedRef<number>;
  /** Store the pending edit now, with its store outcome kept. Runs inside the undo or redo queue slot. */
  flushOutcome: (settle?: boolean) => Promise<StoreOutcome>;
  /** The sync gate's single write queue; undo and redo run inside one slot each. */
  enqueueWrite: <T>(run: (token: FenceToken) => Promise<T>, refused: T) => Promise<T>;
  /** The history's deps the navigation reads and writes run through. */
  history: Pick<
    ExamWorkspaceHistoryDeps,
    | "historyCursor"
    | "install"
    | "isBlocked"
    | "isReadOnly"
    | "isReplacing"
    | "lineageId"
    | "noteExportBlockers"
    | "noteLeaseLost"
    | "onConflict"
    | "replaceCopy"
    | "savedRevision"
    | "shared"
    | "tabId"
    | "workspaceDocument"
  >;
  /** The save status the navigation reports confirmed moves and refusals through. */
  status: {
    clear: () => void;
    confirmed: (document: NativeExamDocument) => void;
    noteRefused: (reason: string) => void;
  };
};

export function useExamWorkspaceHistoryNavigation(deps: ExamWorkspaceHistoryNavigationDeps) {
  const toast = useToast();
  const { history } = deps;

  /**
   * Move the server position to `stepId` and install that step's document,
   * which the move also wrote to the exam file. A stale-cursor 409 keeps the
   * 40-04-09 R9 policy: reload the server copy and stop, without a toast. A
   * 409 that names the edit lease instead turns the tab read-only and keeps
   * the pending edit visible, with no reload. Any other failure toasts
   * `failureCopy` and leaves the copy in place.
   */
  async function moveTo(stepId: string, failureCopy: string): Promise<boolean> {
    const lineageId = history.lineageId();
    const cursor = history.historyCursor.value;
    if (!lineageId || !cursor) {
      return false;
    }
    try {
      const response = await history.shared.moveExamWorkspaceHistoryPosition(lineageId, {
        expectedCursor: cursor,
        stepId,
        tabId: history.tabId(),
      });
      if (history.lineageId() !== lineageId) {
        return false;
      }
      history.noteExportBlockers(response.document.title, response.export_blockers);
      deps.ownCursor.value = response.history.cursor;
      history.historyCursor.value = response.history.cursor;
      deps.baselineId.value = response.history.baseline_step_id;
      deps.stepIds.value = [...response.history.step_ids];
      deps.position.value = response.history.position_step_id;
      history.install(response.document);
      deps.stepDocument.value = response.document;
      deps.status.confirmed(response.document);
      return true;
    } catch (error) {
      if (isEditLeaseHeldError(error)) {
        history.noteLeaseLost();
      } else if (isApiError(error) && error.status === 409) {
        await history.onConflict();
      } else if (isApiError(error) && error.status === 422) {
        // The step changes a placeholder still being converted: undo stops
        // and the status shows Inte sparat with the guard's reason.
        const standing = deps.stepDocument.value ?? history.workspaceDocument.value;
        if (standing === null) {
          toast.failure(failureCopy);
          return false;
        }
        deps.status.noteRefused(refusalReason(standing, error));
      } else {
        toast.failure(failureCopy);
      }
      return false;
    }
  }

  async function undo(): Promise<void> {
    if (!deps.canUndo.value || history.isBlocked() || history.isReplacing() || history.isReadOnly()) {
      return;
    }
    await deps.enqueueWrite(runUndo, undefined);
  }

  /**
   * The raw undo body, run inside one queue slot: locked from before the
   * pending edit is stored, so nothing typed meanwhile is replaced.
   */
  async function runUndo(): Promise<void> {
    // Locked from before the pending edit is stored, so nothing typed meanwhile is replaced.
    deps.navigating.value = true;
    try {
      await history.replaceCopy(async () => {
        const outcome = await deps.flushOutcome();
        if (outcome === "failed") {
          return;
        }
        if (outcome === "refused") {
          // The pending edit can never be a step: discard the refused working
          // copy and stand on the stored step, keeping the saved revision.
          // The refused edit is gone, so this press moves nowhere, keeps the
          // last confirmation, and there is nothing to redo.
          const standing = deps.stepDocument.value;
          if (standing !== null) {
            const revision = history.savedRevision() ?? standing.revision;
            const document = { ...standing, revision };
            history.install(document);
            deps.stepDocument.value = document;
          }
          deps.status.clear();
          return;
        }
        const at = deps.index.value;
        const target = at > 0 ? deps.ids.value[at - 1] : undefined;
        if (target) {
          await moveTo(target, UNDO_FAILURE_COPY);
        }
      });
    } finally {
      deps.navigating.value = false;
    }
  }

  async function redo(): Promise<void> {
    if (!deps.canRedo.value || history.isBlocked() || history.isReplacing() || history.isReadOnly()) {
      return;
    }
    await deps.enqueueWrite(runRedo, undefined);
  }

  /** The raw redo body, run inside one queue slot. */
  async function runRedo(): Promise<void> {
    const target = deps.ids.value[deps.index.value + 1];
    if (!target) {
      return;
    }
    deps.navigating.value = true;
    try {
      await history.replaceCopy(() => moveTo(target, REDO_FAILURE_COPY));
    } finally {
      deps.navigating.value = false;
    }
  }

  return { redo, undo };
}
