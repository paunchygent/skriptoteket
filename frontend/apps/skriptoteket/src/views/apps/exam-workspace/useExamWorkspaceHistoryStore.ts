/**
 * Exam workspace history store handler (TASK-SKRIPT-40-04-14, F2).
 *
 * Domain purpose:
 *   Stores one snapshot through the fenced step store: "stored" when the
 *   server's newest step now holds it (or nothing needed storing), "refused"
 *   when the save rules reject it so it can never be a step, and "failed"
 *   otherwise. Every call carries the queue token it runs under; a retired
 *   answer installs, confirms and clears nothing. The write boundary records
 *   per-piece intent: the confirmed copy C (the step document), the desired
 *   copy D (the working copy), at most one active attempt A (its sent copy,
 *   token and attempt identity, registered synchronously before the transport
 *   runs), and the unresolved published pieces U. A current success installs
 *   C and its history coherently, adopts the server's normalised value per
 *   piece where D still equals the sent copy and preserves D where it differs
 *   (through the refused-edit merger), then discharges A, U and the kept keys
 *   the acknowledgement covers; newer pieces stay pending and are stored
 *   next. A definite non-commit (the save-rule refusal, the 422, a
 *   stale-cursor 409, EDIT_LEASE_HELD) clears A before reporting; an unknown
 *   outcome (a network failure, another error, a rejected promise) moves A's
 *   pieces into U. A late acknowledgement or rejection after retirement has
 *   no authority over C, D, intent or status.
 *
 *   `hasUnconfirmed` is the only definition of confirmation: an active A, a
 *   nonempty U, kept-owned keys, or pieces where D differs from C. D equal to
 *   an old C is not confirmed while A, U or kept keys exist. A network
 *   failure keeps the pending edit; a stale-cursor 409 is reported through
 *   `onConflict` to the sync gate, while an `EDIT_LEASE_HELD` 409 turns the
 *   tab read-only and keeps the edit visible with no reload, toast or retry.
 *   Refusals are decided from the snapshot, with the server's 422 as the
 *   backstop. Storing the working copy ends its pause; storing an owed
 *   snapshot leaves typing's pause running.
 *
 *   Structural-edit snapshots stay owed until stored, oldest first, and a
 *   failed store never merges them. The `storing` flag reads true only while
 *   the active attempt's token is still current (a computed over the fence's
 *   reactive generation), so a store left hanging across a retire no longer
 *   reads as storing and a retired completion cannot clear it under a current
 *   store.
 */

import { computed, shallowRef } from "vue";
import type { ComputedRef, Ref } from "vue";

import { isApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { sameDocument } from "./examWorkspaceConversionMerge";
import { diffPieces } from "./examWorkspaceEditPieces";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { mergeRefusedEdit } from "./examWorkspaceRefusedEditMerge";
import type { FenceToken } from "./examWorkspaceSyncFence";
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
  | "isCurrent"
  | "keptUnstored"
  | "lineageId"
  | "noteExportBlockers"
  | "noteGateStored"
  | "noteLeaseLost"
  | "noteStored"
  | "onConflict"
  | "tabId"
  | "transport"
  | "workspaceDocument"
>;

export type ExamWorkspaceHistoryStoreState = {
  /** The installed step list, baseline first; a store truncates past an undone step. */
  baselineId: Ref<string | null>;
  stepIds: Ref<string[]>;
  /** The stored snapshot the editor stands on; null until the step list is loaded. */
  position: Ref<string | null>;
  /** That step's document; the confirmed copy C. */
  stepDocument: Ref<NativeExamDocument | null>;
  /** The cursor this tab last wrote. */
  ownCursor: Ref<string | null>;
  /** The newest step id; a store past an older standing step drops the redo steps. */
  newestId: ComputedRef<string | null>;
};

/** The save-status half the store reports its outcome through. */
export type ExamWorkspaceHistoryStoreStatus = {
  confirmed: (token: FenceToken, document: NativeExamDocument) => void;
  noteFailed: (token: FenceToken) => void;
  noteLeaseLost: () => void;
  noteRefused: (token: FenceToken, reason: string) => void;
};

export type ExamWorkspaceHistoryStoreHooks = {
  /** Queue the typing pause again after a blocked store. */
  scheduleTyping: () => void;
  /** Store the newer working copy that arrived while a store was in flight. */
  flushNewer: (token: FenceToken) => void;
};

/** One in-flight store: its immutable sent copy, token, identity and owned pieces. */
type ActiveAttempt = {
  /** The attempt identity; a late answer carrying another identity changes nothing. */
  id: number;
  token: FenceToken;
  /** What the transport was asked to store. */
  sent: NativeExamDocument;
  /** The pieces where the sent copy differs from the confirmed copy. */
  pieces: Set<string>;
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
  /** Store the snapshot, or the working copy when it is null, for the queue token. */
  store: (
    token: FenceToken,
    settle?: boolean,
    snapshot?: NativeExamDocument | null,
  ) => Promise<StoreOutcome>;
  /** Store the owed snapshots in order, stopping at the first that fails. */
  storeOwed: (token: FenceToken) => Promise<boolean>;
  /** Hold a structural-edit snapshot until it is stored. */
  pushOwed: (snapshot: NativeExamDocument) => void;
  /** Drop structural snapshots owed from a copy the lease loss retired. */
  dropOwedSnapshots: () => void;
  /** True while a current-generation store is in flight: reads false after a retire. */
  storing: ComputedRef<boolean>;
  /** The only definition of confirmation: an active attempt, unresolved pieces, kept keys or net edits. */
  hasUnconfirmed: () => boolean;
  /** The unresolved published pieces: U plus the active attempt's pieces. */
  publishedPieces: () => Set<string>;
  /** Move the active attempt into U and clear it: the generation retired. */
  abandonAttempt: () => void;
  /** Clear the active attempt and the unresolved pieces: a new exam starts with no intent. */
  resetUnconfirmed: () => void;
} {
  const toast = useToast();
  /** The one active store attempt; null once it settles, is refused or is abandoned. */
  const active = shallowRef<ActiveAttempt | null>(null);
  /** Pieces an earlier store may have changed remotely without confirmation. */
  const unresolved = shallowRef<Set<string>>(new Set());
  let attemptSeq = 0;
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

  /**
   * Fold a retired attempt into the unresolved pieces. Attempts only retire
   * through the gate's fence, so a non-current attempt found here belongs to
   * an older generation whose answer has no authority left.
   */
  function settleAttemptRecord(): void {
    const current = active.value;
    if (current !== null && !deps.isCurrent(current.token)) {
      const next = new Set(unresolved.value);
      for (const piece of current.pieces) {
        next.add(piece);
      }
      unresolved.value = next;
      active.value = null;
    }
  }

  function publishedPieces(): Set<string> {
    settleAttemptRecord();
    const pieces = new Set(unresolved.value);
    const current = active.value;
    if (current !== null && deps.isCurrent(current.token)) {
      for (const piece of current.pieces) {
        pieces.add(piece);
      }
    }
    return pieces;
  }

  function hasUnconfirmed(): boolean {
    settleAttemptRecord();
    const current = active.value;
    if (current !== null && deps.isCurrent(current.token)) {
      return true;
    }
    if (unresolved.value.size > 0) {
      return true;
    }
    if (deps.keptUnstored()) {
      return true;
    }
    return diffPieces(state.stepDocument.value, deps.workspaceDocument.value).size > 0;
  }

  function abandonAttempt(): void {
    settleAttemptRecord();
    const current = active.value;
    if (current !== null) {
      const next = new Set(unresolved.value);
      for (const piece of current.pieces) {
        next.add(piece);
      }
      unresolved.value = next;
      active.value = null;
    }
  }

  function resetUnconfirmed(): void {
    active.value = null;
    unresolved.value = new Set();
  }

  /** A definite non-commit: the attempt proves nothing and owns nothing. */
  function clearAttempt(attemptId: number): void {
    if (active.value?.id === attemptId) {
      active.value = null;
    }
  }

  /** An unknown outcome: the attempt may have committed, so its pieces stay owned. */
  function suspendAttempt(attemptId: number): void {
    const current = active.value;
    if (current !== null && current.id === attemptId) {
      const next = new Set(unresolved.value);
      for (const piece of current.pieces) {
        next.add(piece);
      }
      unresolved.value = next;
      active.value = null;
    }
  }

  async function store(
    token: FenceToken,
    settle = false,
    snapshot: NativeExamDocument | null = null,
  ): Promise<StoreOutcome> {
    if (!deps.isCurrent(token)) {
      return "failed";
    }
    settleAttemptRecord();
    const lineageId = deps.lineageId();
    const cursor = deps.historyCursor.value;
    const document = snapshot ?? deps.workspaceDocument.value;
    const after = state.position.value;
    if (!lineageId || !cursor || !document || after === null) {
      return "failed";
    }
    const undone = after !== state.newestId.value;
    // A snapshot equal to the step document carries nothing new, unless
    // unresolved pieces or kept keys wait for a real cursor-checked store to
    // confirm them. It confirms nothing while any intent is outstanding.
    const awaitsConfirmation = unresolved.value.size > 0 || deps.keptUnstored();
    if (sameContent(document, state.stepDocument.value) && !(settle && undone) && !awaitsConfirmation) {
      if (!hasUnconfirmed()) {
        deps.noteGateStored(token);
      }
      return "stored";
    }
    const refusal = examWorkspaceSaveRefusalCopy(document);
    if (refusal !== null) {
      // A draft the save rules refuse already shows why inline in the editor.
      status.noteRefused(token, refusal);
      return "refused";
    }
    if (deps.isBlocked()) {
      hooks.scheduleTyping();
      return "failed";
    }
    const attemptId = attemptSeq + 1;
    attemptSeq = attemptId;
    active.value = {
      id: attemptId,
      pieces: diffPieces(state.stepDocument.value, document),
      sent: document,
      token,
    };
    let settled: Awaited<ReturnType<typeof deps.transport.storeUndoStep>>;
    try {
      settled = await deps.transport.storeUndoStep(token, lineageId, {
        afterStepId: after,
        document,
        expectedCursor: cursor,
        tabId: deps.tabId(),
      });
    } catch {
      // A rejected promise proves nothing about the commit: keep the pieces.
      suspendAttempt(attemptId);
      owed = [];
      status.noteFailed(token);
      return "failed";
    }
    if (settled.kind === "stale" || !deps.isCurrent(token)) {
      return "failed";
    }
    if (settled.kind === "failed") {
      const error = settled.error;
      if (isEditLeaseHeldError(error)) {
        // Another tab holds the lease: turn read-only and keep the pending
        // edit visible, with no reload, no toast and no retry scheduled. The
        // status leaves `Sparar …` for `Inte sparat` with the lease reason
        // while that edit stays unconfirmed.
        clearAttempt(attemptId);
        status.noteLeaseLost();
        deps.noteLeaseLost();
      } else if (isApiError(error) && error.status === 409) {
        clearAttempt(attemptId);
        await deps.onConflict();
      } else if (isApiError(error) && error.status === 422) {
        // Only the server sees this refusal, so it always toasts.
        clearAttempt(attemptId);
        status.noteRefused(token, refusalReason(document, error));
        toast.failure(error.code === "VALIDATION_ERROR" ? AUTOSAVE_FAILURE_COPY : error.message);
        return "refused";
      } else {
        // The next store sends the newest working copy, not old snapshots.
        suspendAttempt(attemptId);
        owed = [];
        status.noteFailed(token);
      }
      return "failed";
    }
    const current = active.value;
    if (current === null || current.id !== attemptId || !deps.isCurrent(token)) {
      return "failed";
    }
    const sent = current.sent;
    const response = settled.value;
    if (!deps.isCurrent(token)) {
      return "failed";
    }
    // The cursor-checked write committed: prior uncertainty is resolved.
    active.value = null;
    unresolved.value = new Set();
    deps.noteExportBlockers(response.document.title, response.export_blockers);
    state.ownCursor.value = response.history.cursor;
    deps.historyCursor.value = response.history.cursor;
    state.baselineId.value = response.history.baseline_step_id;
    state.stepIds.value = [...response.history.step_ids];
    state.position.value = response.history.position_step_id;
    state.stepDocument.value = response.document;
    status.confirmed(token, response.document);
    deps.noteStored(token, response.document);
    deps.noteGateStored(token);
    if (!deps.isCurrent(token)) {
      return "stored";
    }
    const workingCopy = deps.workspaceDocument.value;
    if (workingCopy !== null && !sameContent(workingCopy, sent)) {
      // Keystrokes typed while the store was in flight stay in the copy: keep
      // the newer pieces over the server's normalised response and store next.
      deps.workspaceDocument.value = mergeRefusedEdit(
        workingCopy,
        diffPieces(sent, workingCopy),
        response.document,
      );
      hooks.flushNewer(token);
    } else {
      // The server normalised the stored copy: install it, so the copies
      // agree and nothing re-stores.
      deps.workspaceDocument.value = response.document;
    }
    return "stored";
  }

  /**
   * Stores the owed snapshots in order and stops at the first that fails, so
   * nothing newer is stored past it; it stays owed for the next write. A
   * refused snapshot is dropped, since no retry can store it.
   */
  async function storeOwed(token: FenceToken): Promise<boolean> {
    if (!deps.isCurrent(token)) {
      return false;
    }
    while (owed.length > 0) {
      if (!deps.isCurrent(token)) {
        return false;
      }
      const next = owed[0];
      if (next === undefined) {
        owed.shift();
        continue;
      }
      const outcome = await store(token, false, next);
      if (!deps.isCurrent(token)) {
        return false;
      }
      if (outcome === "failed") {
        return false;
      }
      if (owed[0] === next) {
        owed.shift();
      }
    }
    return true;
  }

  return {
    abandonAttempt,
    dropOwedSnapshots,
    hasUnconfirmed,
    publishedPieces,
    pushOwed,
    resetUnconfirmed,
    store,
    storeOwed,
    storing: computed(() => active.value !== null && deps.isCurrent(active.value.token)),
  };
}
