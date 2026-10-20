/**
 * Exam workspace sync gate (TASK-SKRIPT-40-04-14, G1b wiring, F1 fence).
 *
 * Domain purpose:
 *   One owner for the exam workspace sync state: the phase (`loading`,
 *   `editing`, `readonly`), the kept refused edit and the single write queue
 *   every save goes through. A write runs only in `editing` for the
 *   generation in which it was queued, one at a time in order; otherwise it
 *   resolves `refused` at once, without calling its run and without awaiting
 *   any read. Every fresh load (document GET, then step-list GET) settles
 *   through the owned fence, so an abandoned read's late answer installs,
 *   merges and changes nothing. With a kept edit the fresh document is held
 *   and only the merge is installed, after both reads succeed; without one
 *   the fresh document is installed at once and shown read-only until the
 *   step list arrives. A failed read keeps `loading`, reports through the
 *   reload-failure port, and retries after 5 s. After a merge install the
 *   gate queues one ordinary store of the working copy through the write
 *   queue; the kept edit clears only when `noteStored` arrives while the
 *   merge token is still current. A network failure of the merged store is
 *   retried by the history's own save retry; a stale-cursor 409 on that
 *   store arrives as `staleConflict` and merges again at the next merge
 *   point. A lease lost during `loading` retires the running load and moves
 *   the gate to `readonly`, so the load can never become editable after a
 *   later reacquisition starts a fresh load.
 *
 * Relationships:
 *   - Calls `mergeRefusedEdit`, which stays the merge owner; G1b passes the
 *     production merge and a production 5 s timer explicitly.
 *   - G1b binds the ports to the existing owners (document, history, lease):
 *     reads install through the document owner, stores through the history,
 *     the lease through `leaseAcquired` and `leaseLost`.
 *   - Owns the sync fence F2 and F3 settle and thread tokens through; the
 *     gate exposes it, but no other port is fenced here yet.
 */

import { computed, ref, shallowRef } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { createSyncFence, type FenceToken, type SyncFence } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceStepListRead } from "./useExamWorkspaceHistoryLoader";

/** The confirmed sync state: no fresh copy and step list, lease held and fresh, or another tab's lease. */
export type ExamWorkspaceSyncGatePhase = "loading" | "editing" | "readonly";

/** The kept refused edit: the step document the edit started from and the refused working copy. */
export type ExamWorkspaceSyncGateKeptEdit = {
  /** The step document the refused edit started from. */
  base: NativeExamDocument;
  /** The refused working copy, kept until a store in the merge generation succeeds. */
  edited: NativeExamDocument;
};

/** The 5 s reload-retry timer; production passes `createSyncGateTimer`. */
export type ExamWorkspaceSyncGateTimer = {
  /** Run `run` after `delayMs`; replaces a pending retry. */
  schedule: (run: () => void, delayMs: number) => void;
  /** Drop a pending retry. */
  cancel: () => void;
};

/** Small ports G1b binds to the existing owners; the specs double them. */
export type ExamWorkspaceSyncGateDeps = {
  /** Whether this tab holds the edit lease now. */
  isLeaseHeld: () => boolean;
  /** Whether the working copy differs from the step document. */
  hasPendingEdit: () => boolean;
  /** The step document the editor stands on, if any. */
  currentStepDocument: () => NativeExamDocument | null;
  /** The working copy in front of the teacher, if any. */
  currentWorkingCopy: () => NativeExamDocument | null;
  /** Drop structural snapshots owed from a copy the lease loss retired. */
  dropOwedSnapshots: () => void;
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
  /** Install a fresh response with no kept edit waiting. */
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
  /** The refused-edit merge; production passes the module default. */
  mergeRefusedEdit: (
    base: NativeExamDocument,
    edited: NativeExamDocument,
    newest: NativeExamDocument,
  ) => NativeExamDocument | null;
  /** Report a failed fresh load (the existing reload-failure toast). */
  notifyReloadFailed: () => void;
  /** The retry timer; production passes `createSyncGateTimer`. */
  timer: ExamWorkspaceSyncGateTimer;
};

/** Delay before a failed fresh load retries. */
export const SYNC_GATE_RELOAD_RETRY_MS = 5000;

/** The production retry timer: one pending retry at a time. */
export function createSyncGateTimer(): ExamWorkspaceSyncGateTimer {
  let handle: ReturnType<typeof setTimeout> | null = null;
  function cancel(): void {
    if (handle !== null) {
      clearTimeout(handle);
      handle = null;
    }
  }
  function schedule(run: () => void, delayMs: number): void {
    cancel();
    handle = setTimeout(() => {
      handle = null;
      run();
    }, delayMs);
  }
  return { cancel, schedule };
}

export function useExamWorkspaceSyncGate(deps: ExamWorkspaceSyncGateDeps) {
  const phase = ref<ExamWorkspaceSyncGatePhase>("loading");
  /** Every input locks while the phase is not `editing`. */
  const editingLocked = computed(() => phase.value !== "editing");
  /** Only the lease notice reads this, so `loading` never shows the lease message. */
  const leaseReadOnly = computed(() => phase.value === "readonly");

  const timer = deps.timer;
  /** The generation owner: every async result settles against its token before touching state. */
  const fence: SyncFence = createSyncFence();

  let lineage: string | null = null;
  const kept = shallowRef<ExamWorkspaceSyncGateKeptEdit | null>(null);
  /** The merge install the kept edit waits for; `noteStored` clears only while it is current. */
  let mergeToken: FenceToken | null = null;
  let disposed = false;
  /** The current generation's tail, so writes run one at a time in order. */
  let tail: Promise<void> = Promise.resolve();

  /** Retire the current generation: outstanding settles resolve `stale` and the next write starts a fresh tail. */
  function retire(): void {
    fence.retire();
    tail = Promise.resolve();
  }

  /**
   * The single write queue. Outside `editing` an entry resolves `refused`
   * at once, without touching the tail. Otherwise the entry captures the
   * current token and runs only when its turn comes while the token is
   * still current and the phase is still `editing`; each generation has its
   * own tail, so a current write never waits behind a retired one. A
   * rejection from `run` reaches this entry's caller but never breaks later
   * entries.
   */
  function enqueueWrite<T>(run: (token: FenceToken) => Promise<T>, refused: T): Promise<T> {
    if (disposed || phase.value !== "editing") {
      return Promise.resolve(refused);
    }
    const token = fence.begin();
    const queue = tail;
    const task = queue.then(() => {
      if (disposed || !fence.isCurrent(token) || phase.value !== "editing") {
        return refused;
      }
      return run(token);
    });
    tail = task.then(
      () => undefined,
      () => undefined,
    );
    return task;
  }

  function startFreshLoad(skipDocument: boolean): void {
    timer.cancel();
    void freshLoad(fence.begin(), skipDocument);
  }

  /**
   * Read the fresh document (unless the cursor arrived with this tab's own
   * fresh copy, and no kept edit needs a fresh merge base) and then the step
   * list, both under the replacing lock. Every read settles through the
   * fence: a retired load installs, merges, resets and changes nothing, and
   * its failure is silent. A current failure resets the step list, reports
   * through the reload-failure port, and retries after 5 s. Every install
   * after an await runs only on a current token.
   */
  async function freshLoad(token: FenceToken, skipDocument: boolean): Promise<void> {
    const lineageId = lineage;
    if (lineageId === null || disposed) {
      return;
    }
    // A kept edit always needs a fresh merge base, even when the cursor came
    // with this tab's own fresh document.
    const wantDocument = !skipDocument || kept.value !== null;
    try {
      await deps.replaceCopy(async () => {
        let fresh: ExamWorkspaceDocumentResponse | null = null;
        if (wantDocument) {
          const documentSettled = await fence.settle(token, deps.readDocument(lineageId));
          if (documentSettled.kind === "stale" || disposed) {
            return;
          }
          if (documentSettled.kind === "failed") {
            throw documentSettled.error;
          }
          fresh = documentSettled.value;
          if (!fence.isCurrent(token) || disposed) {
            return;
          }
          if (kept.value === null) {
            deps.installFresh(token, fresh);
          }
        }
        const base = fresh !== null ? fresh.document : null;
        const stepsSettled = await fence.settle(token, deps.readStepList(lineageId));
        if (stepsSettled.kind === "stale" || disposed) {
          return;
        }
        if (stepsSettled.kind === "failed") {
          deps.resetStepList(token);
          throw stepsSettled.error;
        }
        const read = stepsSettled.value;
        if (!fence.isCurrent(token) || disposed) {
          return;
        }
        deps.applyStepList(token, read, base);
        // The only merge point: a kept edit merges onto the fresh document
        // after both reads succeed, and only the merge install is shown. The
        // phase flips to `editing` first, so the ordinary store the merge
        // queues through the write queue is admitted; the kept edit clears
        // when that store reports back while the merge token is still
        // current.
        const pendingKept = kept.value;
        const freshResponse = fresh;
        let merged: NativeExamDocument | null = null;
        if (pendingKept !== null && freshResponse !== null) {
          merged = deps.mergeRefusedEdit(pendingKept.base, pendingKept.edited, freshResponse.document);
          if (merged === null) {
            kept.value = null;
            mergeToken = null;
          } else {
            deps.installMerged(token, freshResponse, merged);
            mergeToken = token;
          }
        }
        if (!fence.isCurrent(token) || disposed) {
          return;
        }
        phase.value = deps.isLeaseHeld() ? "editing" : "readonly";
        if (merged !== null) {
          deps.requestStore();
        }
      });
    } catch {
      if (!fence.isCurrent(token) || disposed) {
        return;
      }
      deps.notifyReloadFailed();
      timer.schedule(() => {
        if (disposed) {
          return;
        }
        void freshLoad(fence.begin(), false);
      }, SYNC_GATE_RELOAD_RETRY_MS);
    }
  }

  /**
   * Open an exam: another lineage starts a fresh load. When the response
   * already installed the document, only the step list is read.
   */
  function openExam(nextLineageId: string, documentFresh: boolean): void {
    if (disposed) {
      return;
    }
    lineage = nextLineageId;
    kept.value = null;
    mergeToken = null;
    retire();
    phase.value = "loading";
    startFreshLoad(documentFresh);
  }

  /**
   * The lease is held now. A load in flight reads `isLeaseHeld` when it
   * finishes, so in `loading` this is a no-op: the phase is still `loading`
   * only when the lease was never lost since this load started, because a
   * loss during `loading` retires the load and moves the gate to `readonly`.
   * In `readonly` this starts a fresh load.
   */
  function leaseAcquired(): void {
    if (disposed || phase.value !== "readonly") {
      return;
    }
    retire();
    phase.value = "loading";
    startFreshLoad(false);
  }

  /**
   * The lease is gone, or a write was refused with `EDIT_LEASE_HELD`: turn
   * read-only. In `editing`, when a pending edit exists, always (re)capture
   * the kept edit from the current step document and working copy, replacing
   * any older one, and drop owed snapshots. After a merge install the
   * working copy is the merge plus later typing, so the new capture carries
   * both. In `loading` there is no pending edit to capture (inputs are
   * locked) and any kept edit stays; the bump retires the running load, so
   * it can never become editable after a later reacquisition starts a fresh
   * load.
   */
  function leaseLost(): void {
    if (disposed) {
      return;
    }
    if (phase.value === "editing") {
      if (deps.hasPendingEdit()) {
        const base = deps.currentStepDocument();
        const edited = deps.currentWorkingCopy();
        if (base !== null && edited !== null) {
          kept.value = { base, edited };
        }
      }
      deps.dropOwedSnapshots();
      retire();
      phase.value = "readonly";
      return;
    }
    if (phase.value === "loading") {
      retire();
      phase.value = "readonly";
    }
  }

  /**
   * A stale-cursor 409 while editing: back to `loading` for a fresh load.
   * With a kept edit it merges at the merge point; without one the reload
   * replaces the pending edit, as today. The pending edit itself is never
   * captured here.
   */
  function staleConflict(): void {
    if (disposed || phase.value !== "editing") {
      return;
    }
    retire();
    phase.value = "loading";
    startFreshLoad(false);
  }

  /**
   * Another tab moved the history. When the cursor arrived with this tab's
   * own fresh document (a command or Spara som response), the fresh load is
   * the step-list read only; otherwise both reads run.
   */
  function foreignCursor(documentFresh: boolean): void {
    if (disposed) {
      return;
    }
    retire();
    phase.value = "loading";
    startFreshLoad(documentFresh);
  }

  /**
   * A store succeeded while the merge token is still current: the kept edit
   * is recovered. Stores from any other generation leave it pending for the
   * next merge. A stale token changes nothing.
   */
  function noteStored(token: FenceToken): void {
    if (disposed || !fence.isCurrent(token)) {
      return;
    }
    if (kept.value !== null && mergeToken !== null && fence.isCurrent(mergeToken)) {
      kept.value = null;
      mergeToken = null;
    }
  }

  /**
   * Whether the gate holds a kept refused edit that no store has confirmed
   * yet. The save status reads through this so it never reports `Sparat`
   * while the kept edit is unstored.
   */
  const hasKeptEdit = computed(() => kept.value !== null);

  function dispose(): void {
    disposed = true;
    timer.cancel();
    retire();
  }

  return {
    dispose,
    editingLocked,
    enqueueWrite,
    fence,
    foreignCursor,
    hasKeptEdit,
    leaseAcquired,
    leaseLost,
    leaseReadOnly,
    noteStored,
    openExam,
    phase,
    staleConflict,
  };
}
