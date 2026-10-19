/**
 * Exam workspace sync gate (TASK-SKRIPT-40-04-14, G1a skeleton).
 *
 * Domain purpose:
 *   One owner for the exam workspace sync state: the phase (`loading`,
 *   `editing`, `readonly`), a generation number that abandons stale reads and
 *   queued writes, the kept refused edit, and the single write queue every
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
 *   5 s. The merged store is queued through the same write queue and clears
 *   the kept edit only when it reports stored; a network failure keeps the
 *   kept edit and retries on the timer, while a 409 conflict returns to
 *   `loading` for a fresh load that merges again.
 *
 * Relationships:
 *   - Calls `mergeRefusedEdit` (injectable for the spec; production passes
 *     the module default), which stays the merge owner.
 *   - G1b binds the ports to the existing owners (document, history, lease)
 *     and deletes the replaced recovery, queue and loader-join code. This
 *     skeleton wires nothing itself.
 */

import { computed, ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { mergeRefusedEdit as defaultMergeRefusedEdit } from "./examWorkspaceRefusedEditMerge";

/** The confirmed sync state: no fresh copy and step list, lease held and fresh, or another tab's lease. */
export type ExamWorkspaceSyncGatePhase = "loading" | "editing" | "readonly";

/** How the merged store settled: stored, retryable failure, or stale-cursor conflict. */
export type ExamWorkspaceSyncGateStoreOutcome = "stored" | "failed" | "conflict";

/** The kept refused edit: the step document the edit started from and the refused working copy. */
export type ExamWorkspaceSyncGateKeptEdit = {
  /** The step document the refused edit started from. */
  base: NativeExamDocument;
  /** The refused working copy, kept until a merged store succeeds. */
  edited: NativeExamDocument;
};

/** The 5 s reload-retry timer; injectable so the spec drives retries by hand. */
export type ExamWorkspaceSyncGateTimer = {
  /** Run `run` after `delayMs`; replaces a pending retry. */
  schedule: (run: () => void, delayMs: number) => void;
  /** Drop a pending retry. */
  cancel: () => void;
};

/** Small ports G1b binds to the existing owners; the spec doubles them. */
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
  /** Read the fresh server document without installing it. */
  readDocument: (lineageId: string) => Promise<NativeExamDocument>;
  /** Read the fresh step list; the owner applies it to its own state. */
  readSteps: (lineageId: string) => Promise<void>;
  /** Put a fresh or merged document in front of the teacher. */
  installDocument: (document: NativeExamDocument) => void;
  /** Run a replacing read under the existing lock. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
  /** Store the merged document; reports how it settled. */
  storeMerged: (merged: NativeExamDocument) => Promise<ExamWorkspaceSyncGateStoreOutcome>;
  /** The refused-edit merge; defaults to the production merge. */
  mergeRefusedEdit?: (
    base: NativeExamDocument,
    edited: NativeExamDocument,
    newest: NativeExamDocument,
  ) => NativeExamDocument | null;
  /** Report a failed fresh load (the existing reload-failure toast). */
  notifyReloadFailed: () => void;
  /** The retry timer; defaults to a 5 s setTimeout holder. */
  timer?: ExamWorkspaceSyncGateTimer;
};

/** Delay before a failed fresh load retries. */
export const SYNC_GATE_RELOAD_RETRY_MS = 5000;

function defaultTimer(): ExamWorkspaceSyncGateTimer {
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

  const merge = deps.mergeRefusedEdit ?? defaultMergeRefusedEdit;
  const timer = deps.timer ?? defaultTimer();

  let generation = 0;
  let lineage: string | null = null;
  let kept: ExamWorkspaceSyncGateKeptEdit | null = null;
  let disposed = false;
  /** Serializes `enqueueWrite` entries so writes run one at a time in order. */
  let tail: Promise<void> = Promise.resolve();

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
   * list, both under the replacing lock. Every await is generation-guarded:
   * a read for an older generation installs, merges and changes nothing. A
   * failure of either read keeps `loading` with the kept edit untouched,
   * reports through the reload-failure port, and retries after 5 s.
   */
  async function freshLoad(loadGeneration: number, skipDocument: boolean): Promise<void> {
    const lineageId = lineage;
    if (lineageId === null || disposed) {
      return;
    }
    // A kept edit always needs a fresh merge base, even when the cursor came
    // with this tab's own fresh document (unreachable in practice: a kept
    // edit implies `loading`, where no command can run).
    const wantDocument = !skipDocument || kept !== null;
    let newest: NativeExamDocument | null = null;
    let mergedToStore: NativeExamDocument | null = null;
    try {
      await deps.replaceCopy(async () => {
        if (wantDocument) {
          const fresh = await deps.readDocument(lineageId);
          if (disposed || loadGeneration !== generation) {
            return;
          }
          if (kept === null) {
            deps.installDocument(fresh);
          }
          newest = fresh;
        }
        await deps.readSteps(lineageId);
        if (disposed || loadGeneration !== generation) {
          return;
        }
        // The only merge point: a kept edit merges onto the fresh document
        // after both reads succeed, and only the merged result is installed.
        const pendingKept = kept;
        const freshDocument = newest;
        if (pendingKept !== null && wantDocument && freshDocument !== null) {
          const merged = merge(pendingKept.base, pendingKept.edited, freshDocument);
          if (merged === null) {
            kept = null;
          } else {
            deps.installDocument(merged);
            mergedToStore = merged;
          }
        }
        phase.value = deps.isLeaseHeld() ? "editing" : "readonly";
        const merged = mergedToStore;
        if (merged !== null && kept !== null) {
          storeMergedThroughQueue(loadGeneration, merged);
        }
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
   * Queue the merged document through the write queue. It runs because the
   * load just reached `editing`; a lease loss or lineage change before its
   * turn resolves it without running, and its late answer then changes
   * nothing. Only a stored outcome clears the kept edit.
   */
  function storeMergedThroughQueue(loadGeneration: number, merged: NativeExamDocument): void {
    void enqueueWrite<ExamWorkspaceSyncGateStoreOutcome>(
      () => deps.storeMerged(merged),
      "failed",
    ).then(
      (outcome) => settleMergedStore(loadGeneration, merged, outcome),
      () => settleMergedStore(loadGeneration, merged, "failed"),
    );
  }

  function settleMergedStore(
    loadGeneration: number,
    merged: NativeExamDocument,
    outcome: ExamWorkspaceSyncGateStoreOutcome,
  ): void {
    if (disposed || loadGeneration !== generation) {
      return;
    }
    if (outcome === "stored") {
      kept = null;
      return;
    }
    if (outcome === "conflict") {
      // A 409 on the merged store: back to `loading` for a fresh load that
      // merges the still-kept edit again at the next merge point.
      generation += 1;
      phase.value = "loading";
      startFreshLoad(false);
      return;
    }
    // A network failure keeps the kept edit pending and retries the merged
    // store on the timer; the next fresh load would merge it again meanwhile.
    const retryGeneration = generation;
    timer.schedule(() => {
      if (disposed || retryGeneration !== generation) {
        return;
      }
      storeMergedThroughQueue(generation, merged);
    }, SYNC_GATE_RELOAD_RETRY_MS);
  }

  function openExam(nextLineageId: string): void {
    if (disposed) {
      return;
    }
    lineage = nextLineageId;
    kept = null;
    generation += 1;
    phase.value = "loading";
    startFreshLoad(false);
  }

  function leaseAcquired(): void {
    if (disposed || phase.value === "editing") {
      return;
    }
    generation += 1;
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
        kept = { base, edited };
      }
    }
    deps.dropOwedSnapshots();
    generation += 1;
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
    generation += 1;
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
    generation += 1;
    phase.value = "loading";
    startFreshLoad(documentFresh);
  }

  function dispose(): void {
    disposed = true;
    timer.cancel();
    generation += 1;
  }

  return {
    dispose,
    editingLocked,
    enqueueWrite,
    foreignCursor,
    leaseAcquired,
    leaseLost,
    leaseReadOnly,
    openExam,
    phase,
    staleConflict,
  };
}
