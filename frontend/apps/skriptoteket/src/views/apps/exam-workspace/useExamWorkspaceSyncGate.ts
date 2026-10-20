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
 *   merge token is still current. A lease lost during `loading` retires the
 *   running load and moves the gate to `readonly`, so the load can never
 *   become editable after a later reacquisition starts a fresh load. A route
 *   request first settles the latest edit and only then retires; a kept edit
 *   exists whenever the desired copy is unconfirmed, and the merge starts
 *   from the in-flight copy when the server holds the same content.
 *
 * Relationships:
 *   - Calls `mergeRefusedEdit`, which stays the merge owner; G1b passes the
 *     production merge and a production 5 s timer explicitly.
 *   *   - G1b binds the ports to the existing owners (document, history, lease):
 *     reads install through the document owner, stores through the history,
 *     the lease through `leaseAcquired`, `leaseLost` and `leaseRefused`, and
 *     the open-claim wait through `isOpenClaimPending`.
 *   - Owns the sync fence F2 and F3 settle and thread tokens through; the
 *     gate exposes it, but no other port is fenced here yet.
 */

import { computed, ref, shallowRef } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { createSyncFence, type FenceToken, type SyncFence } from "./examWorkspaceSyncFence";
import {
  pickKeptMergeBase,
  requestRouteRetire,
  shouldCaptureKeptEdit,
} from "./examWorkspaceRouteRequest";
import type { ExamWorkspaceStepListRead } from "./useExamWorkspaceHistoryLoader";
import {
  SYNC_GATE_RELOAD_RETRY_MS,
  type ExamWorkspaceSyncGateTimer,
} from "./examWorkspaceSyncGateTimer";
import { createSyncGateQueue } from "./examWorkspaceSyncGateQueue";

/** The confirmed sync state: no fresh copy and step list, lease held and fresh, or another tab's lease. */
export type ExamWorkspaceSyncGatePhase = "loading" | "editing" | "readonly";

/** The kept edit: the confirmed base, the in-flight copy (or null) and the edited working copy. */
export type ExamWorkspaceSyncGateKeptEdit = {
  /** The step document the desired copy stands on. */
  base: NativeExamDocument;
  /** What the in-flight store sent while its answer was unknown. */
  inflight: NativeExamDocument | null;
  /** The working copy in front of the teacher, kept until a store confirms it. */
  edited: NativeExamDocument;
};

/** Small ports G1b binds to the existing owners; the specs double them. */
export type ExamWorkspaceSyncGateDeps = {
  /** Whether this tab holds the edit lease now. */
  isLeaseHeld: () => boolean;
  /**
   * Whether the open claim for the current exam is still in flight. The gate
   * reads this once when a fresh load finishes: while the claim is in flight
   * the load keeps `loading` and lets the claim's outcome decide.
   */
  isOpenClaimPending: () => boolean;
  /** Whether the working copy differs from the step document. */
  hasPendingEdit: () => boolean;
  /** What the in-flight store sent while its answer is unknown, or null. */
  currentInflightDocument: () => NativeExamDocument | null;
  /** Store the latest edit now; true when the server's newest step holds it. */
  settleEdit: () => Promise<boolean>;
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
  /**
   * A fresh load that finished while the open claim was still in flight. The
   * claim's outcome moves the phase without another load; a retired token
   * means the generation moved on and the outcome path ignores it.
   */
  let loadDeferred: FenceToken | null = null;
  let disposed = false;
  const queue = createSyncGateQueue({
    fence,
    isDisposed: () => disposed,
    isEditing: () => phase.value === "editing",
  });

  /** Retire the current generation: outstanding settles resolve `stale` and the next write starts a fresh tail. */
  function retire(): void {
    fence.retire();
    queue.discard();
    // A deferred load belongs to the retired generation; its claim settled
    // stale and can no longer decide without a fresh load.
    loadDeferred = null;
  }

  /**
   * A route request starts its own generation: settle the latest edit first,
   * and only when the store lands retire in the same continuation and hand
   * back the request's token. A request that does not settle retires nothing
   * and gets null. Outside `editing` there is nothing to settle: retire at
   * once. An older open still reading settles stale, so its install and its
   * claim never run.
   */
  function openRequested(): Promise<FenceToken | null> {
    return requestRouteRetire({
      begin: () => fence.begin(),
      isDisposed: () => disposed,
      isEditing: () => phase.value === "editing",
      replaceCopy: deps.replaceCopy,
      retire,
      settleEdit: () => deps.settleEdit(),
    });
  }

  function startFreshLoad(skipDocument: boolean): void {
    timer.cancel();
    void freshLoad(fence.begin(), skipDocument);
  }

  /**
   * Read the fresh document (unless the cursor arrived with this tab's own
   * fresh copy and no kept edit needs a merge base) and then the step list,
   * both under the replacing lock. A retired load installs, merges, resets
   * and changes nothing, and its failure is silent. A current failure resets
   * the step list, reports through the reload-failure port, and retries.
   * Every install after an await runs only on a current token.
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
        // after both reads succeed, from the in-flight copy when the server
        // holds the same content and from the confirmed base otherwise. The
        // phase flips to `editing` first, so the merge's store is admitted;
        // the kept edit clears when that store reports back while current.
        const pendingKept = kept.value;
        const freshResponse = fresh;
        let merged: NativeExamDocument | null = null;
        if (pendingKept !== null && freshResponse !== null) {
          merged = deps.mergeRefusedEdit(
            pickKeptMergeBase(pendingKept, freshResponse.document),
            pendingKept.edited,
            freshResponse.document,
          );
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
        // The open claim for this exam may still be in flight: the lease was
        // not held when this load started, but a first-try claim means no
        // other tab held the exam. An open claim always follows a fresh
        // lineage, whose open cleared any kept edit, so there is no merge to
        // run here. Keep `loading` and let the claim's outcome decide without
        // another load; a load that finishes after the claim concluded behaves
        // as today.
        if (deps.isOpenClaimPending()) {
          loadDeferred = token;
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
   * A reload whose generation retired while it waited hands over: when its
   * exam is still the open one, retire and read it fresh. The load always
   * reads the document, because the install that retired the reload may hold
   * an older copy. In `readonly` it does nothing: the next acquisition
   * reloads anyway.
   */
  function reloadFresh(): void {
    if (disposed || phase.value === "readonly") {
      return;
    }
    retire();
    phase.value = "loading";
    startFreshLoad(false);
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
   * The lease is held now. A fresh load that deferred on the open claim
   * moves to `editing` without another load; a load still in flight reads
   * the held lease when it finishes. In `readonly` this starts a fresh load.
   */
  function leaseAcquired(): void {
    if (disposed) {
      return;
    }
    const deferred = loadDeferred;
    loadDeferred = null;
    if (deferred !== null && fence.isCurrent(deferred) && phase.value === "loading") {
      phase.value = "editing";
      return;
    }
    if (phase.value !== "readonly") {
      return;
    }
    retire();
    phase.value = "loading";
    startFreshLoad(false);
  }

  /**
   * The open claim ended without holding. A fresh load that deferred on that
   * claim moves to `readonly` without another load; a load still in flight
   * concludes as today.
   */
  function leaseRefused(): void {
    if (disposed) {
      return;
    }
    const deferred = loadDeferred;
    loadDeferred = null;
    if (deferred !== null && fence.isCurrent(deferred) && phase.value === "loading") {
      phase.value = "readonly";
    }
  }

  /**
   * Capture the unconfirmed copy as the kept edit and drop owed snapshots. A
   * kept edit exists whenever the desired copy is unconfirmed: the working
   * copy differs from the last confirmed store, or a store is in flight whose
   * answer is unknown. The `editing` branches of `leaseLost`, `pageHidden`
   * and the route retire share this, so a retired holder keeps the same
   * recovery either way.
   */
  function captureKeptEdit(): void {
    const base = deps.currentStepDocument();
    const edited = deps.currentWorkingCopy();
    const inflight = deps.currentInflightDocument();
    if (base !== null && edited !== null && shouldCaptureKeptEdit(deps.hasPendingEdit(), inflight)) {
      kept.value = { base, edited, inflight };
    }
    deps.dropOwedSnapshots();
  }

  /**
   * The lease is gone, or a write was refused with `EDIT_LEASE_HELD`: turn
   * read-only. In `editing` the unconfirmed copy is (re)captured as the kept
   * edit, replacing any older one, and owed snapshots are dropped. After a
   * merge install the working copy is the merge plus later typing, so the new
   * capture carries both. In `loading` there is nothing to capture (inputs
   * are locked) and any kept edit stays; the bump retires the running load,
   * so it can never become editable after a later reacquisition.
   */
  function leaseLost(): void {
    if (disposed) {
      return;
    }
    if (phase.value === "editing") {
      captureKeptEdit();
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
   * The page is going away (`pagehide`): retire the current generation in
   * every live phase, so a pending claim or load settles stale and never
   * unlocks the retired page. In `editing` the unconfirmed copy is captured
   * exactly like `leaseLost`; in `loading` the running load is retired and
   * the gate goes `readonly`; in `readonly` the pending retry claim is
   * retired. A later genuine heartbeat claim still reacquires and loads
   * fresh.
   */
  function pageHidden(): void {
    if (disposed) {
      return;
    }
    if (phase.value === "editing") {
      captureKeptEdit();
    }
    retire();
    phase.value = "readonly";
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

  /** Another tab moved the history: reload, with the document read only when the cursor did not arrive with it. */
  function foreignCursor(documentFresh: boolean): void {
    if (disposed) {
      return;
    }
    retire();
    phase.value = "loading";
    startFreshLoad(documentFresh);
  }

  /** A store in the merge generation recovered the kept edit; other generations leave it pending. */
  function noteStored(token: FenceToken): void {
    if (disposed || !fence.isCurrent(token)) {
      return;
    }
    if (kept.value !== null && mergeToken !== null && fence.isCurrent(mergeToken)) {
      kept.value = null;
      mergeToken = null;
    }
  }

  /** The gate holds an unconfirmed copy; the save status never reports `Sparat` while it does. */
  const hasKeptEdit = computed(() => kept.value !== null);

  function dispose(): void {
    disposed = true;
    timer.cancel();
    retire();
  }

  return {
    dispose,
    editingLocked,
    enqueueWrite: queue.enqueueWrite,
    fence,
    foreignCursor,
    hasKeptEdit,
    leaseAcquired,
    leaseLost,
    leaseReadOnly,
    leaseRefused,
    noteStored,
    openExam,
    openRequested,
    pageHidden,
    phase,
    reloadFresh,
    staleConflict,
  };
}
