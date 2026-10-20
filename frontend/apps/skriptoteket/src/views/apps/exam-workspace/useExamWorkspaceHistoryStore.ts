/**
 * Exam workspace history store handler (TASK-SKRIPT-40-04-14, F1).
 *
 * Domain purpose:
 *   Stores one snapshot through the server's step store: "stored" when the
 *   server's newest step now holds it (or nothing needed storing), "refused"
 *   when the save rules reject it so it can never be a step, and "failed"
 *   otherwise. A network failure keeps the pending edit; a stale-cursor 409
 *   is reported through `onConflict` to the sync gate, while an
 *   `EDIT_LEASE_HELD` 409 turns the tab read-only and keeps the edit visible
 *   with no reload, toast or retry. Refusals are decided from the snapshot,
 *   with the server's 422 as the backstop. Storing the working copy ends its
 *   pause; storing an owed snapshot leaves typing's pause running. A response
 *   never replaces later typing: when the working copy still equals the sent
 *   snapshot, the server's stored copy is installed instead, so nothing
 *   re-stores; when it differs, a store of the newer copy follows.
 *
 *   Structural-edit snapshots stay owed until stored, oldest first, and a
 *   failed store never merges them. The `storing` flag and the owed list live
 *   here; the history owns the retry timer and the flush that runs this
 *   handler inside the gate's write queue.
 */

import { ref } from "vue";
import type { ComputedRef, Ref } from "vue";

import { isApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { sameDocument } from "./examWorkspaceConversionMerge";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { isEditLeaseHeldError } from "./useExamWorkspaceEditLease";
import type { ExamWorkspaceHistoryDeps } from "./useExamWorkspaceHistory";
import {
  AUTOSAVE_FAILURE_COPY,
  refusalReason,
  type StoreOutcome,
} from "./useExamWorkspaceSaveStatus";

export type ExamWorkspaceHistoryStoreDeps = Pick<
  ExamWorkspaceHistoryDeps,
  | "historyCursor"
  | "isBlocked"
  | "lineageId"
  | "noteExportBlockers"
  | "noteGateStored"
  | "noteLeaseLost"
  | "noteStored"
  | "onConflict"
  | "shared"
  | "tabId"
  | "workspaceDocument"
>;

export type ExamWorkspaceHistoryStoreState = {
  /** The installed step list, baseline first; a store truncates past an undone step. */
  baselineId: Ref<string | null>;
  stepIds: Ref<string[]>;
  /** The stored snapshot the editor stands on; null until the step list is loaded. */
  position: Ref<string | null>;
  /** That step's document; a working copy that differs from it is a pending edit. */
  stepDocument: Ref<NativeExamDocument | null>;
  /** The cursor this tab last wrote. */
  ownCursor: Ref<string | null>;
  /** The newest step id; a store past an older standing step drops the redo steps. */
  newestId: ComputedRef<string | null>;
};

/** The save-status half the store reports its outcome through. */
export type ExamWorkspaceHistoryStoreStatus = {
  confirmed: (document: NativeExamDocument) => void;
  noteFailed: () => void;
  noteLeaseLost: () => void;
  noteRefused: (reason: string) => void;
};

export type ExamWorkspaceHistoryStoreHooks = {
  /** Queue the typing pause again after a blocked store. */
  scheduleTyping: () => void;
  /** Store the newer working copy that arrived while a store was in flight. */
  flushNewer: () => void;
};

/** Steps compare without the revision: a step stored before a Spara carries the older one. */
export function sameContent(a: NativeExamDocument | null, b: NativeExamDocument | null): boolean {
  if (a === null || b === null) {
    return a === b;
  }
  return sameDocument({ ...a, revision: 1 }, { ...b, revision: 1 });
}

export function createHistoryStore(
  deps: ExamWorkspaceHistoryStoreDeps,
  state: ExamWorkspaceHistoryStoreState,
  status: ExamWorkspaceHistoryStoreStatus,
  hooks: ExamWorkspaceHistoryStoreHooks,
): {
  /** Store the snapshot, or the working copy when it is null. */
  store: (settle?: boolean, snapshot?: NativeExamDocument | null) => Promise<StoreOutcome>;
  /** Store the owed snapshots in order, stopping at the first that fails. */
  storeOwed: () => Promise<boolean>;
  /** Hold a structural-edit snapshot until it is stored. */
  pushOwed: (snapshot: NativeExamDocument) => void;
  /** Drop structural snapshots owed from a copy the lease loss retired. */
  dropOwedSnapshots: () => void;
  /** True while a store is in flight. */
  storing: Ref<boolean>;
} {
  const toast = useToast();
  const storing = ref(false);
  /**
   * Structural-edit snapshots not stored yet, oldest first: the copy just
   * before the edit, then the copy right after it. Each must be a step before
   * anything newer is stored, so a failed store never merges them.
   */
  let owed: NativeExamDocument[] = [];

  function dropOwedSnapshots(): void {
    owed = [];
  }

  function pushOwed(snapshot: NativeExamDocument): void {
    owed.push(snapshot);
  }

  async function store(settle = false, snapshot: NativeExamDocument | null = null): Promise<StoreOutcome> {
    const lineageId = deps.lineageId();
    const cursor = deps.historyCursor.value;
    const document = snapshot ?? deps.workspaceDocument.value;
    const after = state.position.value;
    if (!lineageId || !cursor || !document || after === null) {
      return "failed";
    }
    const undone = after !== state.newestId.value;
    if (sameContent(document, state.stepDocument.value) && !(settle && undone)) {
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
      hooks.scheduleTyping();
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
      state.ownCursor.value = response.history.cursor;
      deps.historyCursor.value = response.history.cursor;
      state.baselineId.value = response.history.baseline_step_id;
      state.stepIds.value = [...response.history.step_ids];
      state.position.value = response.history.position_step_id;
      state.stepDocument.value = response.document;
      status.confirmed(response.document);
      deps.noteGateStored();
      if (!sameContent(deps.workspaceDocument.value, document)) {
        // Keystrokes typed while the store was in flight stay in the copy;
        // the newer copy is stored next, so the status reads `Sparar …`.
        hooks.flushNewer();
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

  return { dropOwedSnapshots, pushOwed, store, storeOwed, storing };
}
