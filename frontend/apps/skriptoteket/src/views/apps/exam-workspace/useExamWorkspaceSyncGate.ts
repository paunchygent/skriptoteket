/**
 * Exam workspace sync gate (TASK-SKRIPT-40-04-14, G1b wiring, F1 fence).
 *
 * Domain purpose:
 *   One owner for the exam workspace sync state: the phase (`loading`,
 *   `editing`, `readonly`), the kept unconfirmed work and the single write
 *   queue every save goes through. A write runs only in `editing` for the
 *   generation in which it was queued, one at a time in order; otherwise it
 *   resolves `refused` at once, without calling its run and without awaiting
 *   any read. Every fresh load (document GET, then step-list GET) settles
 *   through the owned fence, so an abandoned read's late answer installs,
 *   merges and changes nothing. With kept work the fresh document is held
 *   and only the recovery commit installs, after both reads succeed; without
 *   it the fresh document is installed at once and shown read-only until the
 *   step list arrives. A failed read keeps `loading`, reports through the
 *   reload-failure port, and retries after 5 s. After the recovery commit the
 *   gate queues one ordinary store of the working copy through the write
 *   queue, even when the merge equals the fresh copy; the kept pieces clear
 *   only when a real current store confirms them. A lease lost during
 *   `loading` retires the running load and moves the gate to `readonly`, so
 *   the load can never become editable after a later reacquisition starts a
 *   fresh load. Every document replacement runs through the gate-owned
 *   replacement coordinator: one latest-intent slot behind one locked source
 *   barrier, which alone settles, chooses, retires, opens or adopts, and
 *   publishes the address.
 *
 * Relationships:
 *   - Calls `mergeRefusedEdit` with explicit ownership, which stays the merge
 *     owner; G1b passes the production merge and a production 5 s timer
 *     explicitly.
 *   *   - G1b binds the ports to the existing owners (document, history, lease):
 *     reads install through the document owner, stores through the history,
 *     the lease through `leaseAcquired`, `leaseLost` and `leaseRefused`, and
 *     the open-claim wait through `isOpenClaimPending`.
 *   - Owns the sync fence F2 and F3 settle and thread tokens through; the
 *     gate exposes it, but no other port is fenced here yet.
 *   - Instantiates the replacement coordinator and stays its semantic owner:
 *     the coordinator's barrier ports close over the gate's own state, and
 *     its selection ports arrive as gate deps bound by the editing session.
 */

import { computed, ref } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { createSyncFence, type FenceToken, type SyncFence } from "./examWorkspaceSyncFence";
import { createReplacementCoordinator } from "./examWorkspaceReplacementCoordinator";
import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceReplacementTypes";
import { createSyncGateKept } from "./examWorkspaceSyncGateKept";
import { createSyncGateFreshLoad } from "./examWorkspaceSyncGateFreshLoad";
import type { ExamWorkspaceStepListRead } from "./useExamWorkspaceHistoryLoader";
import {
  SYNC_GATE_RELOAD_RETRY_MS,
  type ExamWorkspaceSyncGateTimer,
} from "./examWorkspaceSyncGateTimer";
import { createSyncGateQueue } from "./examWorkspaceSyncGateQueue";

/** The confirmed sync state: no fresh copy and step list, lease held and fresh, or another tab's lease. */
export type ExamWorkspaceSyncGatePhase = "loading" | "editing" | "readonly";

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
  /** The confirmed copy C the write boundary stands on, if any. */
  confirmedCopy: () => NativeExamDocument | null;
  /** The desired copy D in front of the teacher, if any. */
  desiredCopy: () => NativeExamDocument | null;
  /** The unresolved published pieces: U plus the active attempt's pieces. */
  publishedPieces: () => Set<string>;
  /** Move the active attempt into U and clear it: the generation retired. */
  abandonAttempt: () => void;
  /** Clear the active attempt and the unresolved pieces: a new exam owns new intent. */
  resetUnconfirmed: () => void;
  /** Store the latest edit now; true when the server's newest step holds it. */
  settleEdit: () => Promise<boolean>;
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
  /** Report a failed fresh load (the existing reload-failure toast). */
  notifyReloadFailed: () => void;
  /** The retry timer; production passes `createSyncGateTimer`. */
  timer: ExamWorkspaceSyncGateTimer;
  /** True while a current-generation store is in flight. */
  hasActiveStore: () => boolean;
  /** The installed source: the exam lineage in front of the teacher, if any. */
  installedSource: () => string | null;
  /** The working copy visibly differs from the saved exam. */
  isVisibleDirty: () => boolean;
  /** The only definition of confirmation: no active, unresolved, kept or net intent. */
  hasUnconfirmed: () => boolean;
  /** Read and install the named document for the selection's token. */
  openRouteTarget: (lineageId: string, token: FenceToken) => Promise<ExamWorkspaceRouteOpenOutcome>;
  /** Install a replacement response (route read or copy) without deciding anything. */
  installReplacementDocument: (token: FenceToken, response: ExamWorkspaceDocumentResponse) => void;
  /** Claim the edit lease for the selected lineage. */
  claimSelectedLease: (lineageId: string) => void;
  /** Start the copy POST; null when its guards refuse. */
  beginCopy: (
    sourceLineageId: string,
    name: string,
  ) => Promise<ExamWorkspaceDocumentResponse> | null;
  /** Start the new-exam creation; null when its guards refuse. `isLive`
   * reports whether the creation still holds live replacement authority. */
  beginNewExam: (
    expectedCursor: string | null,
    isLive: () => boolean,
  ) => Promise<ExamWorkspaceDocumentResponse> | null;
  /** Report a current route-open failure (the existing open copy). */
  notifyRouteFailed: () => void;
  /** Report a current route-open target the stored file cannot supply: the
   * teacher sees the download-or-remove notice instead of a toast. */
  notifyRouteUnreadable: (lineageId: string) => void;
  /** Report a current copy failure (the existing Spara som copy). */
  notifyCopyFailed: () => void;
  /** Report a current new-exam failure (the Nytt prov copy). */
  notifyNewExamFailed: () => void;
  /** Release the retired copy selection's busy hold at once. */
  releaseCopyBusy: () => void;
  /** Publish the address; a repeated value is a no-op. */
  projectAddress: (lineageId: string | null) => void;
  /** Resolve once no router navigation is in flight. */
  waitForRouterIdle: () => Promise<void>;
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
  const kept = createSyncGateKept({
    confirmedCopy: () => deps.confirmedCopy(),
    desiredCopy: () => deps.desiredCopy(),
    dropOwedSnapshots: () => deps.dropOwedSnapshots(),
    fence,
    isDisposed: () => disposed,
    lineage: () => lineage,
    publishedPieces: () => deps.publishedPieces(),
  });
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

  const freshLoad = createSyncGateFreshLoad(
    {
      applyStepList: deps.applyStepList,
      installFresh: deps.installFresh,
      installMerged: deps.installMerged,
      isLeaseHeld: deps.isLeaseHeld,
      isOpenClaimPending: deps.isOpenClaimPending,
      mergeRefusedEdit: deps.mergeRefusedEdit,
      notifyReloadFailed: deps.notifyReloadFailed,
      readDocument: deps.readDocument,
      readStepList: deps.readStepList,
      replaceCopy: deps.replaceCopy,
      requestStore: deps.requestStore,
      resetStepList: deps.resetStepList,
      retryDelayMs: SYNC_GATE_RELOAD_RETRY_MS,
      timer,
    },
    {
      fence,
      isDisposed: () => disposed,
      kept: () => kept.kept.value,
      lineage: () => lineage,
      loadDeferred: () => loadDeferred,
      setLoadDeferred: (token) => {
        loadDeferred = token;
      },
      setPhase: (next) => {
        phase.value = next;
      },
    },
  );

  const coordinator = createReplacementCoordinator({
    abandonAttempt: () => deps.abandonAttempt(),
    adoptSelectedOpening: (nextLineageId) => adoptSelectedOpening(nextLineageId),
    beginCopy: (sourceLineageId, name) => deps.beginCopy(sourceLineageId, name),
    beginNewExam: (expectedCursor, isLive) => deps.beginNewExam(expectedCursor, isLive),
    captureKept: () => kept.captureKeptEdit(),
    claimSelectedLease: (nextLineageId) => deps.claimSelectedLease(nextLineageId),
    fence,
    hasActiveStore: () => deps.hasActiveStore(),
    hasUnconfirmed: () => deps.hasUnconfirmed(),
    installedSource: () => deps.installedSource(),
    installReplacementDocument: (token, response) => deps.installReplacementDocument(token, response),
    isDisposed: () => disposed,
    isEditing: () => phase.value === "editing",
    isVisibleDirty: () => deps.isVisibleDirty(),
    notifyCopyFailed: () => deps.notifyCopyFailed(),
    notifyNewExamFailed: () => deps.notifyNewExamFailed(),
    notifyRouteFailed: () => deps.notifyRouteFailed(),
    notifyRouteUnreadable: (lineageId) => deps.notifyRouteUnreadable(lineageId),
    openRouteTarget: (nextLineageId, token) => deps.openRouteTarget(nextLineageId, token),
    projectAddress: (nextLineageId) => deps.projectAddress(nextLineageId),
    recoverRetainedSource: () => recoverRetainedSource(),
    releaseCopyBusy: () => deps.releaseCopyBusy(),
    replaceCopy: deps.replaceCopy,
    retireGeneration: () => retire(),
    settleEdit: () => deps.settleEdit(),
    waitForRouterIdle: () => deps.waitForRouterIdle(),
  });

  /**
   * Open an exam: another lineage starts a fresh load. When the response
   * already installed the document, only the step list is read. The retire
   * ends any coordinator departure the event supersedes.
   */
  function openExam(nextLineageId: string, documentFresh: boolean): void {
    if (disposed) {
      return;
    }
    retire();
    adoptOpening(nextLineageId, documentFresh);
    coordinator.notifySourceRetired();
  }

  /**
   * Adopt the coordinator's selected lineage: another lineage starts a step-list
   * load under the selection's still-current generation. Unlike `openExam`
   * this retires nothing: the selection already retired the source and minted
   * its token, and retiring here would kill it.
   */
  function adoptSelectedOpening(nextLineageId: string): void {
    if (disposed) {
      return;
    }
    adoptOpening(nextLineageId, true);
  }

  /** Share the lineage, kept-reset and load start between a retiring open and
   * a selected adoption; only the retiring open retires the generation. */
  function adoptOpening(nextLineageId: string, documentFresh: boolean): void {
    lineage = nextLineageId;
    kept.kept.value = null;
    deps.resetUnconfirmed();
    phase.value = "loading";
    freshLoad.startFreshLoad(documentFresh);
  }

  /**
   * Recover the coordinator's retained source after its selected target failed:
   * the ordinary fresh-load path (document, then step list) in a new current
   * context. The gate lineage still names the source, whose settled work is
   * intact in front of the teacher.
   */
  function recoverRetainedSource(): void {
    if (disposed) {
      return;
    }
    phase.value = "loading";
    freshLoad.startFreshLoad(false);
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
    freshLoad.startFreshLoad(false);
    coordinator.notifySourceRetired();
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
   * The lease is gone, or a write was refused with `EDIT_LEASE_HELD`: turn
   * read-only. In `editing` the unconfirmed copy is (re)captured as the kept
   * record, replacing any older one, the attempt tracking is frozen into the
   * unresolved pieces, and owed snapshots are dropped. After a recovery
   * commit the working copy is the merge plus later typing, so the new
   * capture carries both. In `loading` there is nothing to capture (inputs
   * are locked) and any kept work stays; the bump retires the running load,
   * so it can never become editable after a later reacquisition.
   */
  function leaseLost(): void {
    if (disposed) {
      return;
    }
    if (phase.value === "editing") {
      kept.captureKeptEdit();
      retire();
      deps.abandonAttempt();
      phase.value = "readonly";
      // The event retired the source generation: a pending barrier or
      // selection is stale, so fail the desired departure safely and keep the
      // source with its address. Never open a different exam for this event.
      coordinator.notifySourceRetired();
      return;
    }
    if (phase.value === "loading") {
      retire();
      deps.abandonAttempt();
      phase.value = "readonly";
      coordinator.notifySourceRetired();
    }
  }

  /**
   * The page is going away (`pagehide`): retire the current generation in
   * every live phase, so a pending claim or load settles stale and never
   * unlocks the retired page. In `editing` the unconfirmed copy is captured
   * exactly like `leaseLost`. A later genuine heartbeat claim still
   * reacquires and loads fresh.
   */
  function pageHidden(): void {
    if (disposed) {
      return;
    }
    if (phase.value === "editing") {
      kept.captureKeptEdit();
    }
    retire();
    deps.abandonAttempt();
    phase.value = "readonly";
    // Late results publish nothing after this point.
    coordinator.notifyPageHidden();
  }

  /**
   * A stale-cursor 409 while editing: with kept or uncertain work, capture
   * it, then back to `loading` for a fresh load. The kept pieces merge at the
   * merge point; without them the reload replaces the pending edit, as
   * today. Recapture retains the kept keys.
   */
  function staleConflict(): void {
    if (disposed || phase.value !== "editing") {
      return;
    }
    const keptHere = kept.kept.value !== null && kept.kept.value.lineage === lineage;
    if (keptHere || deps.publishedPieces().size > 0) {
      kept.captureKeptEdit();
    }
    retire();
    deps.abandonAttempt();
    phase.value = "loading";
    freshLoad.startFreshLoad(false);
    coordinator.notifySourceRetired();
  }

  /** Another tab moved the history: reload, with the document read only when the cursor did not arrive with it. */
  function foreignCursor(documentFresh: boolean): void {
    if (disposed) {
      return;
    }
    retire();
    phase.value = "loading";
    freshLoad.startFreshLoad(documentFresh);
    coordinator.notifySourceRetired();
  }

  /**
   * A store confirmed this document under the current token. The kept record
   * trims itself to the still-outstanding pieces.
   */
  function noteStored(token: FenceToken): void {
    kept.noteStoredBy(token);
  }

  function dispose(): void {
    disposed = true;
    timer.cancel();
    retire();
    coordinator.dispose();
  }

  return {
    currentAddress: coordinator.currentAddress,
    dispose,
    editingLocked,
    enqueueWrite: queue.enqueueWrite,
    fence,
    foreignCursor,
    hasKeptEdit: kept.hasKeptEdit,
    leaseAcquired,
    leaseLost,
    leaseReadOnly,
    leaseRefused,
    noteStored,
    openExam,
    pageHidden,
    phase,
    staleConflict,
    submitRoute: coordinator.submitRoute,
    submitSaveAs: coordinator.submitSaveAs,
    submitNewExam: coordinator.submitNewExam,
  };
}
