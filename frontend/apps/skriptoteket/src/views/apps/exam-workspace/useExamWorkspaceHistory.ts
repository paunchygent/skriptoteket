/**
 * Exam workspace autosave and server-stored undo history.
 *
 * Domain purpose:
 *   One save model (TASK-SKRIPT-40-04-14, items 1, 3 and 6): each teacher
 *   edit becomes a server step, typing after a 900 ms pause and a structural
 *   edit at once; each stored step also overwrites the exam file, so autosave
 *   is Spara. The server keeps at most 100 steps after the import baseline,
 *   so undo survives reload and reopening. Undo first stores any pending
 *   edit, so the pending edit itself can be redone; a stale-cursor 409 reloads
 *   the server copy through `onConflict`, which replaces the pending edit,
 *   and undo stops. A 409 that names the edit lease (`EDIT_LEASE_HELD`)
 *   instead turns the tab read-only and keeps the pending edit visible: no
 *   reload, no retry while read-only. Only the tab that holds the lease
 *   writes; undo and redo stop while read-only.
 *
 *   The history cursor is only a concurrency token: it rotates on every
 *   write and need not name a step. The step the editor stands on is the
 *   server's `position_step_id`. While undo or redo moves the position,
 *   editing is locked through the document owner's `replaceCopy`, so no edit
 *   is typed into a copy the move is about to replace, and AI arrivals that
 *   land meanwhile run again on the step. Departure runs through
 *   `useExamWorkspaceHistoryDeparture`, which owns the held lock lifecycle.
 *   Undo's flush of a pending edit has three outcomes: a network or server
 *   failure stops undo and keeps the pending edit in front of the teacher,
 *   and the store is retried every 5 s and on the next edit; a 422 refusal
 *   discards it, so undo reinstalls the standing step and the refused edit
 *   can never be redone.
 *
 *   No `beforeunload` handler is mounted on the exam-workspace routes (see the
 *   departure module for the `pageshow` release and the disposal rule).
 *
 * Relationships:
 *   - Reads the working copy and the cursor the document composable installs;
 *     every response that carries a cursor this composable did not write
 *     (open, reload, Spara som, parent and change-type commands) reloads the
 *     step list.
 *   - Structural commands call `flush` first, so the server's newest step is
 *     the editor's document; `flush` resolves false when that could not be
 *     established, and a replacing command must then not run.
 *   - The save status (`useExamWorkspaceSaveStatus`) is one computed value
 *     the header shows; undo and redo (`useExamWorkspaceHistoryNavigation`)
 *     move the position instead of storing.
 *   - Each confirmed store and each position move also reports its document
 *     through `noteStored`, so the document owner keeps the saved baseline
 *     (the exam file) on the confirmed snapshot.
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
  /** The server's working copy from the last response; the step the cursor names. */
  serverDocument: Ref<NativeExamDocument | null>;
  historyCursor: Ref<string | null>;
  lineageId: () => string | null;
  savedRevision: () => number | null;
  /** The tab id the edit lease holds; every store and move carries it. */
  tabId: () => string;
  /** True while another tab holds the edit lease: writes wait and undo stops. */
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
  /** Another tab moved the history; reload the exam. */
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
  let chain: Promise<void> = Promise.resolve();
  /**
   * Structural-edit snapshots not stored yet, oldest first: the copy just
   * before the edit, then the copy right after it. Each must be a step before
   * anything newer is stored, so a failed store never merges them.
   */
  let owed: NativeExamDocument[] = [];
  let loadToken = 0;
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

  /** Reload the step list and stand on the fresh server copy; resolves true
   * when the step list and step document match that fresh read, false when
   * the lineage moved on, a newer load started, or the read failed. */
  async function load(lineageId: string): Promise<boolean> {
    const token = ++loadToken;
    const base = deps.serverDocument.value;
    try {
      const history = await deps.shared.getExamWorkspaceHistory(lineageId);
      if (token !== loadToken || deps.lineageId() !== lineageId) {
        return false;
      }
      baselineId.value = history.baseline_step_id;
      stepIds.value = [...history.step_ids];
      position.value = history.position_step_id;
      stepDocument.value = base;
      return stepDocument.value === deps.serverDocument.value;
    } catch {
      if (token === loadToken) {
        reset();
      }
      return false;
    }
  }

  watch(
    [() => deps.lineageId(), deps.historyCursor],
    ([lineageId, cursor], previous) => {
      const [previousLineage] = previous ?? [null, null];
      if (lineageId !== previousLineage) {
        reset();
      }
      if (!lineageId || !cursor) {
        return;
      }
      if (cursor === ownCursor.value && lineageId === previousLineage) {
        return;
      }
      if (lineageId === previousLineage && ownCursor.value !== null && ids.value.includes(cursor)) {
        // A read that started before this tab's last step write echoes an older cursor.
        deps.historyCursor.value = ownCursor.value;
        return;
      }
      // The server replaced the copy, so snapshots owed from the old copy no longer apply.
      owed = [];
      void load(lineageId);
    },
    { immediate: true },
  );

  /**
   * Stores `snapshot`, or the working copy: "stored" when the server's newest
   * step now holds it (or nothing needed storing), "refused" when the save
   * rules reject it, so it can never be a step, and "failed" otherwise: a
   * network or server failure keeps the pending edit, while a stale-cursor
   * 409 reloads the server copy through `onConflict`, which replaces it. A
   * 409 that names the edit lease instead turns the tab read-only and keeps
   *   the pending edit visible, with no reload and no toast; the status reads
   *   `Inte sparat` with the lease reason while that edit stays unconfirmed. A draft
   * the save rules refuse never reaches the server: the refusal is decided
   * from the snapshot itself, with the server's 422 as the backstop for
   * refusals only it can see. The typing timer belongs to the working copy:
   * storing it makes the pause moot, while storing an owed snapshot leaves
   * typing's pause running.
   *
   * A store response never replaces edits made after its snapshot: the step
   * document is set to the confirmed snapshot, so later typing stays pending
   * and a store of the newer copy follows at once.
   */
  async function store(settle = false, snapshot: NativeExamDocument | null = null): Promise<StoreOutcome> {
    if (snapshot === null) {
      clearTimer();
    }
    if (deps.isReadOnly()) {
      // A read-only tab keeps its pending edit visible but never writes: the
      // write would only meet the lease it just lost.
      return "failed";
    }
    const lineageId = deps.lineageId();
    const cursor = deps.historyCursor.value;
    if (lineageId && cursor && position.value === null) {
      // The step list failed to load earlier; without it no step can be stored.
      await load(lineageId);
    }
    const document = snapshot ?? deps.workspaceDocument.value;
    const after = position.value;
    if (!lineageId || !cursor || !document || after === null) {
      return "failed";
    }
    const undone = after !== newestId.value;
    if (sameContent(document, stepDocument.value) && !(settle && undone)) {
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
      if (!sameContent(deps.workspaceDocument.value, response.document)) {
        // Keystrokes typed while the store was in flight stay in the copy;
        // the newer copy is stored next, so the status reads `Sparar …`.
        void flush();
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
      const next = owed[0]!;
      if ((await store(false, next)) === "failed") {
        return false;
      }
      if (owed[0] === next) {
        owed.shift();
      }
    }
    return true;
  }

  function enqueue<T>(run: () => Promise<T>): Promise<T> {
    const next = chain.then(run, run);
    chain = next.then(
      () => undefined,
      () => undefined,
    );
    return next;
  }

  /**
   * Store the pending edit now; resolves after every earlier write, with
   * whether the server's newest step holds the editor's document. Owed
   * structural snapshots are stored first; when one fails, the working copy
   * is not stored and flush resolves false. `settle` also stores an undone
   * step as the newest one, because the server's commands (parents, Byt
   * frågetyp) apply to its newest step.
   */
  function flush(settle = false): Promise<boolean> {
    return flushOutcome(settle).then((outcome) => outcome === "stored");
  }

  /**
   * The flush with its store outcome kept: "refused" when the working copy or
   * an owed snapshot is a draft the save rules refuse, "failed" when a write
   * could not be stored. Undo tells them apart; every other caller only needs
   * whether the server's newest step holds the editor's document. A failed
   * flush rearms the 5 s retry unless the tab turned read-only, in which case
   * the pending edit waits for a takeover instead; a concluded flush clears it.
   */
  function flushOutcome(settle = false): Promise<StoreOutcome> {
    return enqueue(async () => {
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
    });
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
   * structural edit; undo then takes back only the structural edit. A store
   * of `before` that matches the step already stored writes nothing. Both
   * snapshots stay owed until stored, so a failed store of `before` is
   * retried before the edit by the next flush, undo or Spara som. When the
   * last store failed, the next edit stores at once instead of waiting out
   * the pause.
   */
  function noteEdit(structural = false, before: NativeExamDocument | null = null): void {
    if (structural) {
      const after = deps.workspaceDocument.value;
      if (before !== null) {
        owed.push(before);
      }
      if (after !== null) {
        owed.push(after);
      }
      void enqueue(storeOwed);
    } else if (status.hasFailed()) {
      void flush();
    } else {
      schedule();
    }
  }

  const navigation = useExamWorkspaceHistoryNavigation({
    baselineId,
    canRedo,
    canUndo,
    flushOutcome,
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
