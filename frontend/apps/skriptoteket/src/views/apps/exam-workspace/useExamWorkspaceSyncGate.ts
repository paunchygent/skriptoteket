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
 *   fresh load. A route request first captures the kept pieces, then settles
 *   the latest edit and only then retires.
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
 */

import { computed, ref, shallowRef } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { diffPieces } from "./examWorkspaceEditPieces";
import { createSyncFence, type FenceToken, type SyncFence } from "./examWorkspaceSyncFence";
import { requestRouteRetire } from "./examWorkspaceRouteRequest";
import { createSyncGateFreshLoad } from "./examWorkspaceSyncGateFreshLoad";
import type { ExamWorkspaceStepListRead } from "./useExamWorkspaceHistoryLoader";
import {
  SYNC_GATE_RELOAD_RETRY_MS,
  type ExamWorkspaceSyncGateTimer,
} from "./examWorkspaceSyncGateTimer";
import { createSyncGateQueue } from "./examWorkspaceSyncGateQueue";

/** The confirmed sync state: no fresh copy and step list, lease held and fresh, or another tab's lease. */
export type ExamWorkspaceSyncGatePhase = "loading" | "editing" | "readonly";

/** The kept unconfirmed work: the exam it belongs to, an immutable snapshot
 * of the desired copy D, and the owned piece set P (`diffPieces` of the
 * confirmed copy against D, plus published, active and already-kept pieces).
 */
export type ExamWorkspaceSyncGateKeptEdit = {
  /** The exam lineage the desired snapshot belongs to. */
  lineage: string;
  /** The working copy in front of the teacher, kept until a store confirms it. */
  desired: NativeExamDocument;
  /** The owned pieces: desired wins each of them in the recovery commit. */
  pieces: Set<string>;
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
};

/**
 * An immutable snapshot of a document. The working copy is a deep reactive
 * value, which `structuredClone` rejects, so the snapshot goes through JSON;
 * documents are plain server JSON.
 */
function snapshotDocument(document: NativeExamDocument): NativeExamDocument {
  const snapshot: NativeExamDocument = JSON.parse(JSON.stringify(document));
  return snapshot;
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
      kept: () => kept.value,
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

  /**
   * A route request starts its own generation: capture the kept pieces first,
   * then settle the latest edit, and only when the store lands retire in the
   * same continuation and hand back the request's token. A request that does
   * not settle retires nothing and gets null, keeping the captured work.
   * Outside `editing` there is nothing to settle: retire at once. An older
   * open still reading settles stale, so its install and its claim never run.
   */
  function openRequested(): Promise<FenceToken | null> {
    return (async () => {
      if (disposed) {
        return null;
      }
      if (phase.value === "editing") {
        captureKeptEdit();
      }
      const token = await requestRouteRetire({
        begin: () => fence.begin(),
        isDisposed: () => disposed,
        isEditing: () => phase.value === "editing",
        replaceCopy: deps.replaceCopy,
        retire,
        settleEdit: () => deps.settleEdit(),
      });
      if (disposed) {
        return null;
      }
      if (token === null) {
        // The settle did not land: no generation retired, so recapture the
        // post-settle state instead of retiring anything.
        if (phase.value === "editing") {
          captureKeptEdit();
        }
        return null;
      }
      // A generation retired inside the request: freeze attempt tracking into
      // the unresolved pieces, then keep the captured work only while intent
      // stays unconfirmed.
      deps.abandonAttempt();
      if (phase.value === "editing") {
        captureKeptEdit();
      }
      return token;
    })();
  }

  /**
   * Capture the unconfirmed copy as the kept record before any retirement.
   * P is the confirmed-against-desired diff plus published, active and
   * already-kept pieces; with an empty P there is no kept work. The second
   * loss recaptures from the latest D while retaining the kept keys, so a
   * rebase never drops ownership a store has not confirmed.
   */
  function captureKeptEdit(): void {
    const confirmed = deps.confirmedCopy();
    const desired = deps.desiredCopy();
    const lineageId = lineage;
    if (confirmed === null || desired === null || lineageId === null) {
      deps.dropOwedSnapshots();
      return;
    }
    const pieces = new Set<string>([
      ...diffPieces(confirmed, desired),
      ...deps.publishedPieces(),
      ...(kept.value !== null && kept.value.lineage === lineageId ? kept.value.pieces : []),
    ]);
    if (pieces.size === 0) {
      kept.value = null;
    } else {
      kept.value = { desired: snapshotDocument(desired), lineage: lineageId, pieces };
    }
    deps.dropOwedSnapshots();
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
    deps.resetUnconfirmed();
    retire();
    phase.value = "loading";
    freshLoad.startFreshLoad(documentFresh);
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
      captureKeptEdit();
      retire();
      deps.abandonAttempt();
      phase.value = "readonly";
      return;
    }
    if (phase.value === "loading") {
      retire();
      deps.abandonAttempt();
      phase.value = "readonly";
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
      captureKeptEdit();
    }
    retire();
    deps.abandonAttempt();
    phase.value = "readonly";
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
    const keptHere = kept.value !== null && kept.value.lineage === lineage;
    if (keptHere || deps.publishedPieces().size > 0) {
      captureKeptEdit();
    }
    retire();
    deps.abandonAttempt();
    phase.value = "loading";
    freshLoad.startFreshLoad(false);
  }

  /** Another tab moved the history: reload, with the document read only when the cursor did not arrive with it. */
  function foreignCursor(documentFresh: boolean): void {
    if (disposed) {
      return;
    }
    retire();
    phase.value = "loading";
    freshLoad.startFreshLoad(documentFresh);
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
    freshLoad.startFreshLoad(false);
  }

  /**
   * A store confirmed this document under the current token. Keep the kept
   * pieces until a real current store confirms them: recompute the still
   * outstanding pieces against the latest copies, and clear only when no
   * kept piece differs and no published piece stays unresolved. A
   * generation-only acknowledgement for an older snapshot never clears kept
   * work that snapshot did not cover.
   */
  function noteStored(token: FenceToken): void {
    if (disposed || !fence.isCurrent(token)) {
      return;
    }
    const pendingKept = kept.value;
    if (pendingKept === null || pendingKept.lineage !== lineage) {
      return;
    }
    const confirmed = deps.confirmedCopy();
    const desired = deps.desiredCopy();
    if (confirmed === null || desired === null) {
      return;
    }
    const outstanding = [...pendingKept.pieces].filter(
      (piece) =>
        diffPieces(confirmed, desired).has(piece) || deps.publishedPieces().has(piece),
    );
    if (outstanding.length === 0) {
      kept.value = null;
    } else {
      kept.value = {
        desired: snapshotDocument(desired),
        lineage: pendingKept.lineage,
        pieces: new Set(outstanding),
      };
    }
  }

  /** The gate holds unconfirmed work; the save status never reports `Sparat` while it does. */
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
