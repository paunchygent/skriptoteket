/**
 * Exam workspace sync gate fresh load (TASK-SKRIPT-40-04-14, R9-2 recovery).
 *
 * Domain purpose:
 *   The gate-owned fresh load: read the fresh document (unless the cursor
 *   arrived with this tab's own fresh copy and no kept work needs a merge
 *   base) and then the step list, both under the replacing lock. A retired
 *   load installs, merges, resets and changes nothing, and its failure is
 *   silent. A current failure resets the step list, reports through the
 *   reload-failure port, and retries. Every install after an await runs only
 *   on a current token.
 *
 *   The merge point is one coherent recovery commit: admit the fresh
 *   response and step list under the current token, overlay the kept owned
 *   pieces onto the fresh copy through the refused-edit merger, and in one
 *   synchronous install put the fresh copy into the baseline/history and the
 *   merge into the working copy with the current cursor (no cursor-watcher
 *   notification as if external). With no owned pieces the fresh copy
 *   installs anyway and recovery completes. With owned pieces the kept keys
 *   stay until a real current store confirms them, and that store goes
 *   through the ordinary write queue even when the merge equals the fresh
 *   copy, so an unknown published write is never discharged by a no-op.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceSyncGate`, which holds the phase, the kept
 *     record and the fence; this module never retires or captures on its own.
 */

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import type { FenceToken, SyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceStepListRead } from "./useExamWorkspaceHistoryLoader";
import type { ExamWorkspaceSyncGateKeptEdit } from "./useExamWorkspaceSyncGate";
import type { ExamWorkspaceSyncGatePhase } from "./useExamWorkspaceSyncGate";
import type { ExamWorkspaceSyncGateTimer } from "./examWorkspaceSyncGateTimer";

export type ExamWorkspaceSyncGateFreshLoadDeps = {
  /** Read the fresh server response without installing it. */
  readDocument: (lineageId: string) => Promise<ExamWorkspaceDocumentResponse>;
  /** Read the fresh step list without installing it; the gate settles it through the fence. */
  readStepList: (lineageId: string) => Promise<ExamWorkspaceStepListRead>;
  /** Install a settled step-list read for its own generation; stale tokens do nothing. */
  applyStepList: (
    token: FenceToken,
    read: ExamWorkspaceStepListRead,
    base: NativeExamDocument | null,
  ) => void;
  /** Clear the step list after a current-generation read failure; stale tokens do nothing. */
  resetStepList: (token: FenceToken) => void;
  /** Install a fresh response with no kept work waiting. */
  installFresh: (token: FenceToken, response: ExamWorkspaceDocumentResponse) => void;
  /** Apply the fresh response, then install the merged working copy. */
  installMerged: (
    token: FenceToken,
    response: ExamWorkspaceDocumentResponse,
    merged: NativeExamDocument,
  ) => void;
  /** Run a replacing read under the existing lock. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
  /** Queue one ordinary store of the working copy through the write queue. */
  requestStore: () => void;
  /** The refused-edit merge with explicit ownership; production passes the module default. */
  mergeRefusedEdit: (
    desired: NativeExamDocument,
    owned: ReadonlySet<string>,
    newest: NativeExamDocument,
  ) => NativeExamDocument;
  /** Whether this tab holds the edit lease now. */
  isLeaseHeld: () => boolean;
  /** Whether the open claim for the current exam is still in flight. */
  isOpenClaimPending: () => boolean;
  /** Report a failed fresh load (the existing reload-failure toast). */
  notifyReloadFailed: () => void;
  /** The retry timer; production passes `createSyncGateTimer`. */
  timer: ExamWorkspaceSyncGateTimer;
  /** Delay before a failed fresh load retries. */
  retryDelayMs: number;
};

export type ExamWorkspaceSyncGateFreshLoadState = {
  /** The generation owner: every async result settles against its token before touching state. */
  fence: SyncFence;
  /** True once the gate is torn down: a pending load must not leave. */
  isDisposed: () => boolean;
  /** The exam lineage the load belongs to; null before the first open. */
  lineage: () => string | null;
  /** The kept unconfirmed work, if any. */
  kept: () => ExamWorkspaceSyncGateKeptEdit | null;
  /** Move the gate phase once the load or the claim outcome decides. */
  setPhase: (phase: ExamWorkspaceSyncGatePhase) => void;
  /** A load that finished while the open claim was still in flight. */
  loadDeferred: () => FenceToken | null;
  /** Hold or clear the deferred load. */
  setLoadDeferred: (token: FenceToken | null) => void;
};

export function createSyncGateFreshLoad(
  deps: ExamWorkspaceSyncGateFreshLoadDeps,
  state: ExamWorkspaceSyncGateFreshLoadState,
) {
  function startFreshLoad(skipDocument: boolean): void {
    deps.timer.cancel();
    void freshLoad(state.fence.begin(), skipDocument);
  }

  /**
   * Read the fresh document (unless the cursor arrived with this tab's own
   * fresh copy and no kept work needs a merge base) and then the step list,
   * both under the replacing lock. The only merge point runs after both
   * reads succeed: the kept owned pieces overlay the fresh copy, the fresh
   * copy lands in the baseline/history and the merge in the working copy in
   * one synchronous install. The phase flips to `editing` first, so the
   * recovery store is admitted; the kept pieces clear only when a real
   * current store confirms them.
   */
  async function freshLoad(token: FenceToken, skipDocument: boolean): Promise<void> {
    const lineageId = state.lineage();
    if (lineageId === null || state.isDisposed()) {
      return;
    }
    // Kept work always needs a fresh merge base, even when the cursor came
    // with this tab's own fresh document.
    const wantDocument = !skipDocument || state.kept() !== null;
    try {
      await deps.replaceCopy(async () => {
        let fresh: ExamWorkspaceDocumentResponse | null = null;
        if (wantDocument) {
          const documentSettled = await state.fence.settle(token, deps.readDocument(lineageId));
          if (documentSettled.kind === "stale" || state.isDisposed()) {
            return;
          }
          if (documentSettled.kind === "failed") {
            throw documentSettled.error;
          }
          fresh = documentSettled.value;
          if (!state.fence.isCurrent(token) || state.isDisposed()) {
            return;
          }
          if (state.kept() === null) {
            deps.installFresh(token, fresh);
          }
        }
        const base = fresh !== null ? fresh.document : null;
        const stepsSettled = await state.fence.settle(token, deps.readStepList(lineageId));
        if (stepsSettled.kind === "stale" || state.isDisposed()) {
          return;
        }
        if (stepsSettled.kind === "failed") {
          deps.resetStepList(token);
          throw stepsSettled.error;
        }
        const read = stepsSettled.value;
        if (!state.fence.isCurrent(token) || state.isDisposed()) {
          return;
        }
        deps.applyStepList(token, read, base);
        const keptNow = state.kept();
        const pendingKept = keptNow !== null && keptNow.lineage === lineageId ? keptNow : null;
        const freshResponse = fresh;
        if (pendingKept !== null && freshResponse !== null) {
          const merged = deps.mergeRefusedEdit(
            pendingKept.desired,
            pendingKept.pieces,
            freshResponse.document,
          );
          deps.installMerged(token, freshResponse, merged);
        }
        if (!state.fence.isCurrent(token) || state.isDisposed()) {
          return;
        }
        // The open claim for this exam may still be in flight: the lease was
        // not held when this load started, but a first-try claim means no
        // other tab held the exam. An open claim always follows a fresh
        // lineage, whose open cleared any kept work, so there is no merge to
        // run here. Keep `loading` and let the claim's outcome decide without
        // another load; a load that finishes after the claim concluded behaves
        // as today.
        if (deps.isOpenClaimPending()) {
          state.setLoadDeferred(token);
          return;
        }
        state.setPhase(deps.isLeaseHeld() ? "editing" : "readonly");
        if (pendingKept !== null) {
          deps.requestStore();
        }
      });
    } catch {
      if (!state.fence.isCurrent(token) || state.isDisposed()) {
        return;
      }
      deps.notifyReloadFailed();
      deps.timer.schedule(() => {
        if (state.isDisposed()) {
          return;
        }
        void freshLoad(state.fence.begin(), false);
      }, deps.retryDelayMs);
    }
  }

  return { freshLoad, startFreshLoad };
}
