/**
 * Exam workspace autosave and server-stored undo history.
 *
 * Domain purpose:
 *   One save model (TASK-SKRIPT-40-04-14, items 1, 3 and 6): each teacher
 *   edit becomes a server step, typing after a 900 ms pause and a structural
 *   edit at once; each stored step also overwrites the exam file, so autosave
 *   is Spara. The server keeps at most 100 steps after the import baseline,
 *   so undo survives reload and reopening. Undo first stores any pending
 *   edit, so the pending edit itself can be redone; a stale-cursor 409 is
 *   reported through `onConflict` to the sync gate, which reloads the server
 *   copy, and undo stops. A 409 that names the edit lease
 *   (`EDIT_LEASE_HELD`) instead turns the tab read-only and keeps the pending
 *   edit visible: no reload, no retry while read-only. Every write runs
 *   through the sync gate's single queue, so outside `editing` a write
 *   resolves `failed` at once with no read and no wait.
 *
 *   The history cursor is only a concurrency token: it rotates on every
 *   write and need not name a step. The step the editor stands on is the
 *   server's `position_step_id`. While undo or redo moves the position,
 *   editing is locked through the document owner's `replaceCopy`, so no edit
 *   is typed into a copy the move is about to replace, and AI arrivals that
 *   land meanwhile run again on the step. Departure runs through
 *   `useExamWorkspaceHistoryDeparture`, which owns the held lock lifecycle.
 *   Undo's flush of a pending edit has three outcomes: a network or server
 *   failure stops undo and keeps the pending edit, retried every 5 s and on
 *   the next edit; a 422 refusal discards it, so undo reinstalls the
 *   standing step and the refused edit can never be redone.
 *
 * Relationships:
 *   - Reads the working copy and the cursor the document composable installs;
 *     the step list is reloaded by the sync gate's fresh load, which stands
 *     the editor on the fresh server copy. A cursor the gate installed
 *     itself is consumed through `noteInstalledCursor`; any other installed
 *     cursor (a conversion revision) makes the gate read the step list.
 *   - Structural commands call `flush` first, so the server's newest step is
 *     the editor's document; `flush` resolves false when that could not be
 *     established, and a replacing command must then not run.
 *   - The save status (`useExamWorkspaceSaveStatus`) is one computed value
 *     the header shows; undo and redo (`useExamWorkspaceHistoryNavigation`)
 *     move the position instead of storing.
 *   - Each confirmed store also reports its document through `noteStored`,
 *     so the document owner keeps the saved baseline (the exam file) on the
 *     confirmed snapshot, and through `noteGateStored`, so the sync gate
 *     clears a merged kept edit in the merge generation.
 */

import { computed, onScopeDispose, ref, shallowRef } from "vue";
import type { Ref } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { ExamWorkspaceFencedTransport } from "./examWorkspaceFencedTransport";
import { watchHistoryCursor } from "./useExamWorkspaceHistoryCursor";
import { useExamWorkspaceHistoryDeparture } from "./useExamWorkspaceHistoryDeparture";
import { useExamWorkspaceHistoryNavigation } from "./useExamWorkspaceHistoryNavigation";
import type { FenceToken } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceStepListRead } from "./useExamWorkspaceHistoryLoader";
import { createHistoryStore, sameContent } from "./useExamWorkspaceHistoryStore";
import {
  useExamWorkspaceSaveStatus,
  type StoreOutcome,
} from "./useExamWorkspaceSaveStatus";
import type { ExamWorkspaceTitleVerdict } from "./useExamWorkspaceTitleVerdict";

export const EXAM_WORKSPACE_TYPING_PAUSE_MS = 900;

export type ExamWorkspaceHistoryDeps = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  historyCursor: Ref<string | null>;
  lineageId: () => string | null;
  savedRevision: () => number | null;
  /** The tab id the edit lease holds; every store and move carries it. */
  tabId: () => string;
  /** The merged working copy reached the server in the merge generation. */
  noteGateStored: (token: FenceToken) => void;
  /**
   * A response installed this cursor. True when the sync gate installed it
   * itself through a fresh load: the event is consumed and nothing changes.
   * Otherwise the gate reads the step list for the foreign cursor.
   */
  noteInstalledCursor: (lineageId: string, cursor: string) => boolean;
  /** The sync gate's single write queue; outside `editing` entries resolve refused at once. */
  enqueueWrite: <T>(run: (token: FenceToken) => Promise<T>, refused: T) => Promise<T>;
  /** True while the token's generation is still current; fenced installs do nothing for stale tokens. */
  isCurrent: (token: FenceToken) => boolean;
  /** True while the tab may not write: the gate refuses queued writes outside `editing`. */
  isReadOnly: () => boolean;
  /** A write met `EDIT_LEASE_HELD`: turn read-only and keep the pending edit. */
  noteLeaseLost: () => void;
  /** The fenced step store, move and command calls; no unfenced write remains. */
  transport: ExamWorkspaceFencedTransport;
  /** True while an import or a save may not be interleaved with a step write; excludes the replacing lock. */
  isBlocked: () => boolean;
  /** Another undo, redo or server command is replacing the copy; undo and redo wait for it. */
  isReplacing: () => boolean;
  /** True for a guest exam, whose saved status names the browser instead of Mina filer. */
  isGuest: () => boolean;
  /** The sync gate holds a refused edit no store has confirmed. */
  keptUnstored: () => boolean;
  /** Run a read that replaces the copy: locks editing and keeps arrivals that land meanwhile. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
  /** Put a stored step's document in front of the teacher. */
  install: (token: FenceToken, document: NativeExamDocument) => void;
  /** A store or a position move confirmed this document; the file holds it now. */
  noteStored: (token: FenceToken, document: NativeExamDocument) => void;
  /** The export gate's verdict on a stored step, for the title blocker. */
  noteExportBlockers: ExamWorkspaceTitleVerdict;
  /** Another undo, redo or server command replaced the copy; the gate reloads. */
  onConflict: () => Promise<void>;
  /**
   * The new-picture registry: `bytesFor` names the unsent picture bytes the
   * next store must carry, and `noteSent` marks them sent once a committed
   * answer carried them.
   */
  newPictures: {
    bytesFor: (document: NativeExamDocument) => Record<string, Blob>;
    noteSent: (assetIds: readonly string[]) => void;
  };
};

export function useExamWorkspaceHistory(deps: ExamWorkspaceHistoryDeps) {
  const baselineId = ref<string | null>(null);
  const stepIds = ref<string[]>([]);
  /** The stored snapshot the editor stands on; null until the step list is loaded. */
  const position = ref<string | null>(null);
  /** That step's document; a working copy that differs from it is a pending edit. */
  const stepDocument = shallowRef<NativeExamDocument | null>(null);
  const navigating = ref(false);
  /** The cursor this tab last wrote; a read echoing an older cursor is ignored. */
  const ownCursor = ref<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;
  /** True once the history's scope is disposed: a pending departure must not leave. */
  let disposed = false;

  const ids = computed(() => (baselineId.value ? [baselineId.value, ...stepIds.value] : []));
  const index = computed(() => (position.value ? ids.value.indexOf(position.value) : -1));
  const pending = computed(
    () =>
      deps.workspaceDocument.value !== null &&
      stepDocument.value !== null &&
      !sameContent(deps.workspaceDocument.value, stepDocument.value),
  );
  const newestId = computed(() => ids.value[ids.value.length - 1] ?? null);
  const ready = computed(() => position.value !== null && !navigating.value && !deps.isReadOnly());
  const canUndo = computed(() => ready.value && (pending.value || index.value > 0));
  const canRedo = computed(
    () => ready.value && !pending.value && index.value >= 0 && index.value < ids.value.length - 1,
  );

  const storeHandler = createHistoryStore(
    deps,
    { baselineId, newestId, ownCursor, position, stepDocument, stepIds },
    {
      confirmed: (token, document) => status.confirmed(token, document),
      noteFailed: (token) => status.noteFailed(token),
      noteLeaseLost: () => status.noteLeaseLost(),
      noteRefused: (token, reason) => status.noteRefused(token, reason),
    },
    {
      flushNewer: (token) => {
        if (deps.isCurrent(token)) {
          // A running typing pause owns newer typing: leave it until the
          // pause, so a store acknowledgement never closes the burst early.
          if (timer !== null) {
            return;
          }
          void flush();
        }
      },
      scheduleTyping: () => schedule(),
    },
  );
  const status = useExamWorkspaceSaveStatus({
    hasUnconfirmed: () => storeHandler.hasUnconfirmed(),
    isCurrent: deps.isCurrent,
    isGuest: deps.isGuest,
    keptUnstored: deps.keptUnstored,
    noteStored: deps.noteStored,
    pending: () => pending.value,
    storing: computed(() => storeHandler.storing.value),
  });

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function reset(): void {
    clearTimer();
    status.clear();
    storeHandler.dropOwedSnapshots();
    baselineId.value = null;
    stepIds.value = [];
    position.value = null;
    stepDocument.value = null;
  }

  /** Drop structural snapshots owed from a copy the lease loss retired. */
  function dropOwedSnapshots(): void {
    storeHandler.dropOwedSnapshots();
  }

  /**
   * Install a settled step-list read for its own generation: the baseline,
   * the step ids, the standing step and the fresh server copy the editor
   * stands on. A stale token changes nothing.
   */
  function applySteps(
    token: FenceToken,
    read: ExamWorkspaceStepListRead,
    base: NativeExamDocument | null,
  ): void {
    if (!deps.isCurrent(token)) {
      return;
    }
    baselineId.value = read.baselineId;
    stepIds.value = [...read.stepIds];
    position.value = read.position;
    stepDocument.value = base;
  }

  /**
   * Clear the step list after a current-generation read failure, so the
   * gate's fresh-load retry starts from no standing step. A stale token
   * changes nothing.
   */
  function resetSteps(token: FenceToken): void {
    if (!deps.isCurrent(token)) {
      return;
    }
    reset();
  }

  watchHistoryCursor(
    deps,
    { ids, ownCursor },
    reset,
    dropOwedSnapshots,
  );

  /**
   * Store the pending edit now; resolves after every earlier write, with
   * whether the server's newest step holds the editor's document. Owed
   * structural snapshots are stored first; when one fails, the working copy
   * is not stored and flush resolves false. `settle` also stores an undone
   * step as the newest one, which the server's commands apply to.
   */
  function flush(settle = false): Promise<boolean> {
    return flushOutcome(settle).then((outcome) => outcome === "stored");
  }

  /**
   * The flush with its store outcome kept: "refused" when the working copy or
   * an owed snapshot is a draft the save rules refuse, "failed" when a write
   * could not be stored. Undo tells them apart; every other caller only needs
   * whether the server's newest step holds the editor's document. A failed
   * flush rearms the 5 s retry unless the tab may not write; a concluded
   * flush clears it.
   */
  function flushOutcome(settle = false): Promise<StoreOutcome> {
    return deps.enqueueWrite((token) => flushOutcomeInner(token, settle), "failed");
  }

  /**
   * The raw flush body, run inside one queue slot. The newer-typing
   * follow-up and undo call this directly: they already hold a queue slot,
   * so queuing again would wait on itself. A retired token stores nothing
   * and schedules no retry. A structural flush leaves a working copy whose
   * typing pause still runs until the pause: the burst keeps its pause and
   * its one-step undo grouping, while owed snapshots are still stored at
   * once. Every other caller forces the working-copy store, so explicit
   * flush, undo, departure and retry semantics are unchanged.
   */
  async function flushOutcomeInner(token: FenceToken, settle = false, structural = false): Promise<StoreOutcome> {
    if (!deps.isCurrent(token)) {
      return "failed";
    }
    if (!(await storeHandler.storeOwed(token))) {
      if (!deps.isCurrent(token)) {
        return "failed";
      }
      if (!deps.isReadOnly()) {
        status.scheduleRetry(() => void flush());
      }
      return "failed";
    }
    if (structural && !settle && timer !== null && pending.value) {
      // Newer typing arrived while owed snapshots drained and its pause
      // still runs: leave the working copy until the pause fires.
      return "stored";
    }
    // Storing the working copy ends its pause; owed snapshots keep it running.
    clearTimer();
    const outcome = await storeHandler.store(token, settle);
    if (!deps.isCurrent(token)) {
      return "failed";
    }
    if (outcome === "failed") {
      if (!deps.isReadOnly()) {
        status.scheduleRetry(() => void flush());
      }
    } else if (outcome === "stored" && !storeHandler.hasUnconfirmed()) {
      status.clear();
    }
    return outcome;
  }

  function schedule(): void {
    clearTimer();
    timer = setTimeout(() => {
      timer = null;
      void flush();
    }, EXAM_WORKSPACE_TYPING_PAUSE_MS);
  }

  const departure = useExamWorkspaceHistoryDeparture({
    flush: (settle = false) => flush(settle),
    hasUnconfirmed: () => storeHandler.hasUnconfirmed(),
    isNavigating: () => navigating.value,
    isReplacing: deps.isReplacing,
    replaceCopy: deps.replaceCopy,
    isDisposed: () => disposed,
  });

  /**
   * A teacher edit happened: typing waits for a pause; a structural edit is a
   * step now, holding the document as it was right after that edit, so two
   * quick structural edits stay two steps. Typing still waiting for its pause
   * is stored first as its own step, from `before`, the copy just before the
   * structural edit; undo then takes back only the structural edit. Both
   * snapshots stay owed until stored; a store of `before` that already
   * matches writes nothing. The structural autosave runs through the flush
   * body, so a first failed store arms the 5 s retry. Once a store failed,
   * the backlog is dropped and the next edit flushes the newest working copy
   * at once instead of waiting out the pause; undo steps made during an
   * outage then collapse into one step, which is accepted.
   */
  function noteEdit(structural = false, before: NativeExamDocument | null = null): void {
    if (status.hasFailed()) {
      // A failed store drops the backlog: the next store sends the newest copy.
      storeHandler.dropOwedSnapshots();
      void flush();
    } else if (structural) {
      const after = deps.workspaceDocument.value;
      if (before !== null) {
        storeHandler.pushOwed(before);
      }
      if (after !== null) {
        storeHandler.pushOwed(after);
      }
      void deps.enqueueWrite((token) => flushOutcomeInner(token, false, true), "failed");
    } else {
      schedule();
    }
  }

  const navigation = useExamWorkspaceHistoryNavigation({
    baselineId,
    canRedo,
    canUndo,
    enqueueWrite: deps.enqueueWrite,
    flushOutcome: (token, settle = false) => flushOutcomeInner(token, settle),
    isCurrent: deps.isCurrent,
    history: {
      historyCursor: deps.historyCursor,
      install: deps.install,
      isBlocked: deps.isBlocked,
      isCurrent: deps.isCurrent,
      isReadOnly: deps.isReadOnly,
      isReplacing: deps.isReplacing,
      lineageId: deps.lineageId,
      noteExportBlockers: deps.noteExportBlockers,
      noteLeaseLost: deps.noteLeaseLost,
      noteStored: deps.noteStored,
      onConflict: deps.onConflict,
      replaceCopy: deps.replaceCopy,
      savedRevision: deps.savedRevision,
      tabId: deps.tabId,
      transport: deps.transport,
      workspaceDocument: deps.workspaceDocument,
    },
    ids,
    index,
    navigating,
    ownCursor,
    position,
    status: {
      clear: status.clear,
      confirmed: status.confirmed,
      noteRefused: status.noteRefused,
    },
    stepDocument,
    stepIds,
  });

  onScopeDispose(() => {
    disposed = true;
    clearTimer();
    status.dispose();
    departure.dispose();
  });

  return {
    abandonAttempt: () => storeHandler.abandonAttempt(),
    applySteps,
    canRedo,
    canUndo,
    /** The confirmed copy C the write boundary stands on. */
    confirmedCopy: () => stepDocument.value,
    depart: departure.depart,
    /** The desired copy D in front of the teacher. */
    desiredCopy: () => deps.workspaceDocument.value,
    dropOwedSnapshots,
    flush,
    /** The only definition of confirmation: no active, unresolved, kept or net intent. */
    hasUnconfirmed: computed(() => storeHandler.hasUnconfirmed()),
    navigating: computed(() => navigating.value),
    /** The snapshot the editor stands on; null until the step list is loaded. */
    position: computed(() => position.value),
    noteEdit,
    pending,
    /** The unresolved published pieces: U plus the active attempt's pieces. */
    publishedPieces: () => storeHandler.publishedPieces(),
    redo: navigation.redo,
    resetSteps,
    /** Clear the active attempt and the unresolved pieces: a new exam owns new intent. */
    resetUnconfirmed: () => storeHandler.resetUnconfirmed(),
    saveStatus: status.saveStatus,
    saveText: status.saveText,
    /** The step's document; a working copy that differs from it is a pending edit. */
    stepDocument: computed(() => stepDocument.value),
    storing: computed(() => storeHandler.storing.value),
    undo: navigation.undo,
  };
}
