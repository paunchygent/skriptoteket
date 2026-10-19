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

import { computed, onScopeDispose, ref, shallowRef, watch } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { sameDocument } from "./examWorkspaceConversionMerge";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import type { ExamWorkspaceSharedStore } from "./examWorkspaceStore";
import { isEditLeaseHeldError } from "./useExamWorkspaceEditLease";
import { useExamWorkspaceHistoryDeparture } from "./useExamWorkspaceHistoryDeparture";
import { useExamWorkspaceHistoryNavigation } from "./useExamWorkspaceHistoryNavigation";
import { createHistoryLoader } from "./useExamWorkspaceHistoryLoader";
import {
  AUTOSAVE_FAILURE_COPY,
  refusalReason,
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
  noteGateStored: () => void;
  /**
   * A response installed this cursor. True when the sync gate installed it
   * itself through a fresh load: the event is consumed and nothing changes.
   * Otherwise the gate reads the step list for the foreign cursor.
   */
  noteInstalledCursor: (lineageId: string, cursor: string) => boolean;
  /** The sync gate's single write queue; outside `editing` entries resolve refused at once. */
  enqueueWrite: <T>(run: () => Promise<T>, refused: T) => Promise<T>;
  /** True while the tab may not write: the gate refuses queued writes outside `editing`. */
  isReadOnly: () => boolean;
  /** A write met `EDIT_LEASE_HELD`: turn read-only and keep the pending edit. */
  noteLeaseLost: () => void;
  /** The shared store half the history reads and writes run through. */
  shared: ExamWorkspaceSharedStore;
  /** True while an import or a save may not be interleaved with a step write; excludes the replacing lock. */
  isBlocked: () => boolean;
  /** Another undo, redo or server command is replacing the copy; undo and redo wait for it. */
  isReplacing: () => boolean;
  /** True for a guest exam, whose saved status names the browser instead of Mina filer. */
  isGuest: () => boolean;
  /** Run a read that replaces the copy: locks editing and keeps arrivals that land meanwhile. */
  replaceCopy: <T>(run: () => Promise<T>) => Promise<T>;
  /** Put a stored step's document in front of the teacher. */
  install: (document: NativeExamDocument) => void;
  /** A store or a position move confirmed this document; the file holds it now. */
  noteStored: (document: NativeExamDocument) => void;
  /** The export gate's verdict on a stored step, for the title blocker. */
  noteExportBlockers: ExamWorkspaceTitleVerdict;
  /** Another undo, redo or server command replaced the copy; the gate reloads. */
  onConflict: () => Promise<void>;
};

/** Steps compare without the revision: a step stored before a Spara carries the older one. */
function sameContent(a: NativeExamDocument | null, b: NativeExamDocument | null): boolean {
  if (a === null || b === null) {
    return a === b;
  }
  return sameDocument({ ...a, revision: 1 }, { ...b, revision: 1 });
}

export function useExamWorkspaceHistory(deps: ExamWorkspaceHistoryDeps) {
  const toast = useToast();
  const baselineId = ref<string | null>(null);
  const stepIds = ref<string[]>([]);
  /** The stored snapshot the editor stands on; null until the step list is loaded. */
  const position = ref<string | null>(null);
  /** That step's document; a working copy that differs from it is a pending edit. */
  const stepDocument = shallowRef<NativeExamDocument | null>(null);
  const navigating = ref(false);
  const storing = ref(false);
  /** The cursor this tab last wrote; a read echoing an older cursor is ignored. */
  const ownCursor = ref<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;
  /**
   * Structural-edit snapshots not stored yet, oldest first: the copy just
   * before the edit, then the copy right after it. Each must be a step before
   * anything newer is stored, so a failed store never merges them.
   */
  let owed: NativeExamDocument[] = [];
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

  const status = useExamWorkspaceSaveStatus({
    isGuest: deps.isGuest,
    noteStored: deps.noteStored,
    pending: () => pending.value,
    storing: computed(() => storing.value),
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
    owed = [];
    baselineId.value = null;
    stepIds.value = [];
    position.value = null;
    stepDocument.value = null;
  }

  /** Drop structural snapshots owed from a copy the lease loss retired. */
  function dropOwedSnapshots(): void {
    owed = [];
  }

  const { load } = createHistoryLoader(
    deps,
    { baselineId, position, stepDocument, stepIds },
    reset,
  );

  watch(
    [() => deps.lineageId(), deps.historyCursor],
    ([lineageId, cursor], previous) => {
      const [previousLineage] = previous ?? [null, null];
      if (lineageId !== previousLineage) {
        // Another exam: drop the old list. The editing session starts the
        // gate's fresh load for the new lineage.
        reset();
        return;
      }
      if (!lineageId || !cursor) {
        return;
      }
      if (cursor === ownCursor.value) {
        return;
      }
      if (deps.noteInstalledCursor(lineageId, cursor)) {
        // The gate's own install: consume the event and change nothing. This
        // runs before the echo guard below, because the step list the gate
        // just read already contains the fresh cursor.
        return;
      }
      if (ownCursor.value !== null && ids.value.includes(cursor)) {
        // A read that started before this tab's last step write echoes an older cursor.
        deps.historyCursor.value = ownCursor.value;
        return;
      }
      // The server replaced the copy, so snapshots owed from the old copy no longer apply.
      owed = [];
    },
    { immediate: true },
  );

  /**
   * Stores `snapshot`, or the working copy: "stored" when the server's newest
   * step now holds it (or nothing needed storing), "refused" when the save
   * rules reject it so it can never be a step, and "failed" otherwise. A
   * network failure keeps the pending edit; a stale-cursor 409 is reported
   * through `onConflict` to the gate, while an `EDIT_LEASE_HELD` 409 turns
   * the tab read-only and keeps the edit visible with no reload, toast or
   * retry. Refusals are decided from the snapshot, with the server's 422 as
   * the backstop. Storing the working copy ends its pause; storing an owed
   * snapshot leaves typing's pause running. A response never replaces later
   * typing: when the working copy still equals the sent snapshot, the
   * server's stored copy is installed instead, so nothing re-stores; when it
   * differs, a store of the newer copy follows through the same queue slot.
   */
  async function store(settle = false, snapshot: NativeExamDocument | null = null): Promise<StoreOutcome> {
    if (snapshot === null) {
      clearTimer();
    }
    const lineageId = deps.lineageId();
    const cursor = deps.historyCursor.value;
    const document = snapshot ?? deps.workspaceDocument.value;
    const after = position.value;
    if (!lineageId || !cursor || !document || after === null) {
      return "failed";
    }
    const undone = after !== newestId.value;
    if (sameContent(document, stepDocument.value) && !(settle && undone)) {
      deps.noteGateStored();
      return "stored";
    }
    const refusal = examWorkspaceSaveRefusalCopy(document);
    if (refusal !== null) {
      // A draft the save rules refuse already shows why inline in the editor.
      status.noteRefused(refusal);
      return "refused";
    }
    if (deps.isBlocked()) {
      schedule();
      return "failed";
    }
    storing.value = true;
    try {
      const response = await deps.shared.storeExamWorkspaceUndoStep(lineageId, {
        afterStepId: after,
        document,
        expectedCursor: cursor,
        tabId: deps.tabId(),
      });
      if (deps.lineageId() !== lineageId) {
        return "failed";
      }
      deps.noteExportBlockers(response.document.title, response.export_blockers);
      ownCursor.value = response.history.cursor;
      deps.historyCursor.value = response.history.cursor;
      baselineId.value = response.history.baseline_step_id;
      stepIds.value = [...response.history.step_ids];
      position.value = response.history.position_step_id;
      stepDocument.value = response.document;
      status.confirmed(response.document);
      deps.noteGateStored();
      if (!sameContent(deps.workspaceDocument.value, document)) {
        // Keystrokes typed while the store was in flight stay in the copy;
        // the newer copy is stored next, so the status reads `Sparar …`.
        void flush();
      } else {
        // The server normalised the stored copy: install it, so the copies
        // agree and nothing re-stores.
        deps.workspaceDocument.value = response.document;
      }
      return "stored";
    } catch (error) {
      if (isEditLeaseHeldError(error)) {
        // Another tab holds the lease: turn read-only and keep the pending
        // edit visible, with no reload, no toast and no retry scheduled. The
        // status leaves `Sparar …` for `Inte sparat` with the lease reason
        // while that edit stays unconfirmed.
        status.noteLeaseLost();
        deps.noteLeaseLost();
      } else if (isApiError(error) && error.status === 409) {
        await deps.onConflict();
      } else if (isApiError(error) && error.status === 422) {
        // Only the server sees this refusal, so it always toasts.
        status.noteRefused(refusalReason(document, error));
        toast.failure(error.code === "VALIDATION_ERROR" ? AUTOSAVE_FAILURE_COPY : error.message);
        return "refused";
      } else {
        // The next store sends the newest working copy, not old snapshots.
        owed = [];
        status.noteFailed();
      }
      return "failed";
    } finally {
      storing.value = false;
    }
  }

  /**
   * Stores the owed snapshots in order and stops at the first that fails, so
   * nothing newer is stored past it; it stays owed for the next write. A
   * refused snapshot is dropped, since no retry can store it.
   */
  async function storeOwed(): Promise<boolean> {
    while (owed.length > 0) {
      const next = owed[0];
      if (next === undefined) {
        owed.shift();
        continue;
      }
      if ((await store(false, next)) === "failed") {
        return false;
      }
      if (owed[0] === next) {
        owed.shift();
      }
    }
    return true;
  }

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
    return deps.enqueueWrite(() => flushOutcomeInner(settle), "failed");
  }

  /**
   * The raw flush body, run inside one queue slot. The newer-typing
   * follow-up and undo call this directly: they already hold a queue slot,
   * so queuing again would wait on itself.
   */
  async function flushOutcomeInner(settle = false): Promise<StoreOutcome> {
    if (!(await storeOwed())) {
      if (!deps.isReadOnly()) {
        status.scheduleRetry(() => void flush());
      }
      return "failed";
    }
    const outcome = await store(settle);
    if (outcome === "failed") {
      if (!deps.isReadOnly()) {
        status.scheduleRetry(() => void flush());
      }
    } else if (outcome === "stored") {
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
    pending: () => pending.value,
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
   * matches writes nothing. Once a store failed, the backlog is
   * dropped and the next edit flushes the newest working copy at once instead
   * of waiting out the pause; undo steps made during an outage then collapse
   * into one step, which is accepted.
   */
  function noteEdit(structural = false, before: NativeExamDocument | null = null): void {
    if (status.hasFailed()) {
      // A failed store drops the backlog: the next store sends the newest copy.
      owed = [];
      void flush();
    } else if (structural) {
      const after = deps.workspaceDocument.value;
      if (before !== null) {
        owed.push(before);
      }
      if (after !== null) {
        owed.push(after);
      }
      void deps.enqueueWrite(() => storeOwed(), false);
    } else {
      schedule();
    }
  }

  const navigation = useExamWorkspaceHistoryNavigation({
    baselineId,
    canRedo,
    canUndo,
    enqueueWrite: deps.enqueueWrite,
    flushOutcome: flushOutcomeInner,
    history: {
      historyCursor: deps.historyCursor,
      install: deps.install,
      isBlocked: deps.isBlocked,
      isReadOnly: deps.isReadOnly,
      isReplacing: deps.isReplacing,
      lineageId: deps.lineageId,
      noteExportBlockers: deps.noteExportBlockers,
      noteLeaseLost: deps.noteLeaseLost,
      onConflict: deps.onConflict,
      replaceCopy: deps.replaceCopy,
      savedRevision: deps.savedRevision,
      shared: deps.shared,
      tabId: deps.tabId,
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
    canRedo,
    canUndo,
    depart: departure.depart,
    dropOwedSnapshots,
    flush,
    load,
    navigating: computed(() => navigating.value),
    /** The snapshot the editor stands on; null until the step list is loaded. */
    position: computed(() => position.value),
    noteEdit,
    pending,
    redo: navigation.redo,
    saveStatus: status.saveStatus,
    saveText: status.saveText,
    /** The step's document; a working copy that differs from it is a pending edit. */
    stepDocument: computed(() => stepDocument.value),
    storing: computed(() => storing.value),
    undo: navigation.undo,
  };
}
