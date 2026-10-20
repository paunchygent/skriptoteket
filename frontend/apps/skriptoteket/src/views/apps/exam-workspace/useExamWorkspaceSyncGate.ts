/**
 * Exam workspace sync gate (TASK-SKRIPT-40-04-14, G1b wiring).
 *
 * Domain purpose:
 *   One owner for the exam workspace sync state: the phase (`loading`,
 *   `editing`, `readonly`), a generation number that abandons stale reads and
 *   queued writes, the kept refused edit and the single write queue every
 *   save goes through. A write runs only in `editing` for the generation in
 *   which it was queued, one at a time in order; otherwise it resolves
 *   `refused` at once, without calling its run and without awaiting any read.
 *   Every fresh load (document GET, then step-list GET) runs under the deps'
 *   `replaceCopy` lock and checks the generation after each await, so an
 *   abandoned read's late answer installs, merges and changes nothing. With a
 *   kept edit the fresh document is held and only the merge is installed,
 *   after both reads succeed; without one the fresh document is installed at
 *   once and shown read-only until the step list arrives. A failed read keeps
 *   `loading`, reports through the reload-failure port, and retries after
 *   5 s. After a merge install the gate queues one ordinary store of the
 *   working copy through the write queue; the kept edit clears only when
 *   `noteStored` arrives in the generation of that merge install. A network
 *   failure of the merged store is retried by the history's own save retry;
 *   a stale-cursor 409 on that store arrives as `staleConflict` and merges
 *   again at the next merge point.
 *
 * Relationships:
 *   - Calls `mergeRefusedEdit`, which stays the merge owner; G1b passes the
 *     production merge and a production 5 s timer explicitly.
 *   - G1b binds the ports to the existing owners (document, history, lease):
 *     reads install through the document owner, stores through the history,
 *     the lease through `leaseAcquired` and `leaseLost`.
 */

import { computed, ref, shallowRef } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  NativeExamDocument,
} from "../../../api/examWorkspace";

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
  /** Read the fresh step list; the owner applies it, standing on `base`. */
  readSteps: (lineageId: string, base: NativeExamDocument | null) => Promise<void>;
  /** Install a fresh response with no kept edit waiting. */
  installFresh: (response: ExamWorkspaceDocumentResponse) => void;
  /** Apply the fresh response, then install the merged working copy. */
  installMerged: (response: ExamWorkspaceDocumentResponse, merged: NativeExamDocument) => void;
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

  let generation = 0;
  let lineage: string | null = null;
  const kept = shallowRef<ExamWorkspaceSyncGateKeptEdit | null>(null);
  /** The generation whose merge install the kept edit waits for; `noteStored` clears only in it. */
  let mergeGeneration: number | null = null;
  let disposed = false;
  /** Serializes `enqueueWrite` entries so writes run one at a time in order. */
  let tail: Promise<void> = Promise.resolve();
  /**
   * Resolves the abandonment race of the latest fresh load. Every generation
   * bump resolves and clears it, so an abandoned load leaves its replacing
   * scope at once instead of pinning the editing lock behind a hung read.
   */
  let abandonPendingLoad: (() => void) | null = null;

  /** Move to the next generation, releasing the latest load's read race. */
  function bumpGeneration(): void {
    generation += 1;
    const abandon = abandonPendingLoad;
    abandonPendingLoad = null;
    if (abandon !== null) {
      abandon();
    }
  }

  /**
   * The single write queue. An entry runs only in `editing` for the
   * generation in which it was queued; otherwise it resolves `refused` at
   * once, without calling `run` and without awaiting any read. A rejection
   * from `run` reaches this entry's caller but never breaks later entries.
   */
  function enqueueWrite<T>(run: () => Promise<T>, refused: T): Promise<T> {
    const queuedGeneration = generation;
    const task = tail.then(() => {
      if (disposed || queuedGeneration !== generation || phase.value !== "editing") {
        return refused;
      }
      return run();
    });
    tail = task.then(
      () => undefined,
      () => undefined,
    );
    return task;
  }

  function startFreshLoad(skipDocument: boolean): void {
    timer.cancel();
    void freshLoad(generation, skipDocument);
  }

  /**
   * Read the fresh document (unless the cursor arrived with this tab's own
   * fresh copy, and no kept edit needs a fresh merge base) and then the step
   * list, both under the replacing lock. Every read races the generation:
   * when another event moves on, the load leaves its scope at once, so an
   * abandoned read's hung transport never pins the editing lock, and its
   * late answer installs, merges and changes nothing. Every await is also
   * generation-guarded. A failure of either read keeps `loading` with the
   * kept edit untouched, reports through the reload-failure port, and
   * retries after 5 s.
   */
  async function freshLoad(loadGeneration: number, skipDocument: boolean): Promise<void> {
    const lineageId = lineage;
    if (lineageId === null || disposed) {
      return;
    }
    // A kept edit always needs a fresh merge base, even when the cursor came
    // with this tab's own fresh document.
    const wantDocument = !skipDocument || kept.value !== null;
    let resolveAbandoned: (() => void) | null = null;
    const abandoned = new Promise<void>((resolve) => {
      resolveAbandoned = resolve;
    });
    abandonPendingLoad = () => {
      const resolve = resolveAbandoned;
      resolveAbandoned = null;
      if (resolve !== null) {
        resolve();
      }
    };
    const abandonedRace = (): Promise<string> => abandoned.then((): string => "abandoned");
    let fresh: ExamWorkspaceDocumentResponse | null = null;
    try {
      await deps.replaceCopy(async () => {
        if (wantDocument) {
          const documentRead = deps.readDocument(lineageId);
          const documentOutcome = await Promise.race([
            documentRead.then(
              (): string => "document",
              (error: unknown): string => {
                throw error;
              },
            ),
            abandonedRace(),
          ]);
          if (documentOutcome === "abandoned" || disposed || loadGeneration !== generation) {
            return;
          }
          fresh = await documentRead;
          if (disposed || loadGeneration !== generation) {
            return;
          }
          if (kept.value === null) {
            deps.installFresh(fresh);
          }
        }
        const base = fresh !== null ? fresh.document : null;
        const stepsRead = deps.readSteps(lineageId, base);
        const stepsOutcome = await Promise.race([
          stepsRead.then(
            (): string => "steps",
            (error: unknown): string => {
              throw error;
            },
          ),
          abandonedRace(),
        ]);
        if (stepsOutcome === "abandoned" || disposed || loadGeneration !== generation) {
          return;
        }
        await stepsRead;
        // The only merge point: a kept edit merges onto the fresh document
        // after both reads succeed, and only the merge install is shown. The
        // merged working copy then reaches the server through one ordinary
        // store; the kept edit clears when that store reports back in this
        // generation.
        const pendingKept = kept.value;
        const freshResponse = fresh;
        if (pendingKept !== null && freshResponse !== null) {
          const merged = deps.mergeRefusedEdit(pendingKept.base, pendingKept.edited, freshResponse.document);
          if (merged === null) {
            kept.value = null;
            mergeGeneration = null;
          } else {
            deps.installMerged(freshResponse, merged);
            mergeGeneration = loadGeneration;
            deps.requestStore();
          }
        }
        phase.value = deps.isLeaseHeld() ? "editing" : "readonly";
      });
    } catch {
      if (disposed || loadGeneration !== generation) {
        return;
      }
      deps.notifyReloadFailed();
      timer.schedule(() => {
        if (disposed) {
          return;
        }
        void freshLoad(generation, false);
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
    mergeGeneration = null;
    bumpGeneration();
    phase.value = "loading";
    startFreshLoad(documentFresh);
  }

  /**
   * The lease is held now. A load in flight reads `isLeaseHeld` when it
   * finishes, so in `loading` this is a no-op; in `readonly` it starts a
   * fresh load. Opening an exam with a successful claim therefore reads the
   * document once.
   */
  function leaseAcquired(): void {
    if (disposed || phase.value !== "readonly") {
      return;
    }
    bumpGeneration();
    phase.value = "loading";
    startFreshLoad(false);
  }

  /**
   * The lease is gone, or a write was refused with `EDIT_LEASE_HELD`: turn
   * read-only. When a pending edit exists, always (re)capture the kept edit
   * from the current step document and working copy, replacing any older
   * one, and drop owed snapshots. After a merge install the working copy is
   * the merge plus later typing, so the new capture carries both.
   */
  function leaseLost(): void {
    if (disposed || phase.value !== "editing") {
      return;
    }
    if (deps.hasPendingEdit()) {
      const base = deps.currentStepDocument();
      const edited = deps.currentWorkingCopy();
      if (base !== null && edited !== null) {
        kept.value = { base, edited };
      }
    }
    deps.dropOwedSnapshots();
    bumpGeneration();
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
    bumpGeneration();
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
    bumpGeneration();
    phase.value = "loading";
    startFreshLoad(documentFresh);
  }

  /**
   * A store in the merge generation succeeded: the kept edit is recovered.
   * Stores from any other generation leave it pending for the next merge.
   */
  function noteStored(): void {
    if (disposed) {
      return;
    }
    if (kept.value !== null && mergeGeneration !== null && mergeGeneration === generation) {
      kept.value = null;
      mergeGeneration = null;
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
    bumpGeneration();
  }

  return {
    dispose,
    editingLocked,
    enqueueWrite,
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
