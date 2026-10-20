/**
 * Exam workspace save status.
 *
 * Domain purpose:
 *   One computed save status for the one save model (TASK-SKRIPT-40-04-14,
 *   item 6): `Sparar …` while an edit is pending or being stored, `Sparat
 *   HH:MM` once the confirmed snapshot equals the copy in front of the
 *   teacher, and `Inte sparat` with the reason when a store failed, was
 *   refused, met the edit lease held by the other tab while the edit was
 *   still unconfirmed, or left a refused edit the sync gate still holds. A
 *   store response never replaces edits made after its snapshot: the status
 *   reads `Sparat` only when the confirmed snapshot equals the
 *   current copy. After a network or server failure the pending edit stays
 *   and the store is retried every 5 s and on the next edit; after a lease
 *   loss the tab is read-only, so no retry is scheduled and none is promised.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceHistory`, which reports every concluded
 *     store and move through `confirmed`, `noteFailed`, `noteRefused` and
 *     `noteLeaseLost`, and rearms the retry through `scheduleRetry`.
 *   - The header shows `saveText` with `saveStatus.detail` as its tooltip.
 */

import { computed, ref, watch } from "vue";
import type { ComputedRef } from "vue";

import { isApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { examWorkspaceGuestSaveStatus } from "./examWorkspaceGuestDraft";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import type { FenceToken } from "./examWorkspaceSyncFence";

export const AUTOSAVE_FAILURE_COPY = "Ändringarna kunde inte sparas. Vi försöker igen automatiskt.";

/** A tab that lost the lease with an edit not stored: no retry is promised. */
export const LEASE_LOST_COPY =
  "Ändringen sparades inte eftersom provet redigeras i den andra fliken.";

/** The pending-save hint the Öppna drawer and the details drawer share. */
export const PENDING_SAVE_COPY = "Vänta tills ändringarna har sparats.";

/** A failed store is retried this often until it succeeds. */
export const EXAM_WORKSPACE_SAVE_RETRY_MS = 5000;

const SAVE_TIME = new Intl.DateTimeFormat("sv-SE", { hour: "2-digit", minute: "2-digit" });

export type StoreOutcome = "stored" | "refused" | "failed";

export type ExamWorkspaceSaveStatus =
  | { state: "saving"; detail: null }
  | { state: "saved"; detail: string | null; savedAt: string | null }
  | { state: "unsaved"; detail: string };

export type ExamWorkspaceSaveStatusDeps = {
  /** True for a guest exam, whose saved status names the browser instead of Mina filer. */
  isGuest: () => boolean;
  /** The sync gate holds a refused edit no store has confirmed. */
  keptUnstored: () => boolean;
  /** True while the token's generation is still current; stale installs do nothing. */
  isCurrent: (token: FenceToken) => boolean;
  /** A store or a position move confirmed this document; the file holds it now. */
  noteStored: (token: FenceToken, document: NativeExamDocument) => void;
  /** True while the working copy differs from the confirmed snapshot. */
  pending: () => boolean;
  /** True while a store or a position move is in flight. */
  storing: ComputedRef<boolean>;
};

/**
 * The refusal reason for the status tooltip: the save rule's Swedish copy
 * when the draft itself is refused, the guard's own message when a step
 * changes a placeholder still being converted, else the generic failure copy.
 * The guard is told apart by its dedicated `CONVERSION_IN_PROGRESS` code
 * (`ErrorCode` on the server); a 422 carrying `item_ids` is the same refusal.
 */
export function refusalReason(snapshot: NativeExamDocument, error: unknown): string {
  const copy = examWorkspaceSaveRefusalCopy(snapshot);
  if (copy !== null) {
    return copy;
  }
  if (isApiError(error) && (error.code === "CONVERSION_IN_PROGRESS" || hasItemIds(error.details))) {
    return error.message;
  }
  return AUTOSAVE_FAILURE_COPY;
}

function hasItemIds(details: unknown): boolean {
  return typeof details === "object" && details !== null && "item_ids" in details;
}

export function useExamWorkspaceSaveStatus(deps: ExamWorkspaceSaveStatusDeps) {
  const toast = useToast();
  /** When the last store or move was confirmed, as an ISO timestamp. */
  const lastSavedAt = ref<string | null>(null);
  /** The refusal reason of the last concluded store; null once a store succeeds. */
  const lastRefusal = ref<string | null>(null);
  /** True since the last concluded store failed; cleared once a store succeeds. */
  const lastFailure = ref(false);
  /**
   * True since a store met `EDIT_LEASE_HELD` with an edit still unconfirmed.
   * The tab turns read-only and keeps that edit visible, so the status reads
   * `Inte sparat` with the lease reason instead of `Sparar …`.
   */
  const leaseLostWithPendingEdit = ref(false);
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  /**
   * One computed save status: `Sparar …` while an edit is pending or being
   * stored, `Inte sparat` with the reason once a store concluded refused,
   * failed or lost the lease with the edit still unconfirmed, or while the
   * sync gate still holds a refused edit, else `Sparat HH:MM`. A concluded
   * refusal, failure or lease loss pins `Inte sparat` until a store succeeds, even while newer edits are pending.
   * The lease loss is the operative reason while the tab is read-only, so it
   * reads before a refusal or failure pinned earlier.
   */
  const saveStatus = computed<ExamWorkspaceSaveStatus>(() => {
    if (deps.keptUnstored()) {
      // The gate's refused edit is stored by no confirmed snapshot yet: the
      // status keeps `Inte sparat` with the lease reason, even while its
      // merged store is in flight.
      return { state: "unsaved", detail: LEASE_LOST_COPY };
    }
    if (deps.storing.value) {
      return { state: "saving", detail: null };
    }
    if (leaseLostWithPendingEdit.value && deps.pending()) {
      return { state: "unsaved", detail: LEASE_LOST_COPY };
    }
    if (lastRefusal.value !== null) {
      return { state: "unsaved", detail: lastRefusal.value };
    }
    if (lastFailure.value) {
      return { state: "unsaved", detail: AUTOSAVE_FAILURE_COPY };
    }
    if (deps.pending()) {
      return { state: "saving", detail: null };
    }
    return {
      state: "saved",
      detail: lastSavedAt.value === null ? null : SAVE_TIME.format(new Date(lastSavedAt.value)),
      savedAt: lastSavedAt.value,
    };
  });

  /**
   * The header's status text: `Sparar …`, `Sparat HH:MM` (or the guest form
   * `Sparat i webbläsaren HH:MM` for a guest exam), or `Inte sparat`.
   */
  const saveText = computed(() => {
    const status = saveStatus.value;
    if (status.state === "saving") {
      return "Sparar …";
    }
    if (status.state === "unsaved") {
      return "Inte sparat";
    }
    if (deps.isGuest()) {
      return examWorkspaceGuestSaveStatus(status.savedAt ?? "");
    }
    return status.detail === null ? "Sparat" : `Sparat ${status.detail}`;
  });

  function clearRetryTimer(): void {
    if (retryTimer !== null) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
  }

  function confirmed(token: FenceToken, document: NativeExamDocument): void {
    if (!deps.isCurrent(token)) {
      return;
    }
    lastSavedAt.value = new Date().toISOString();
    lastRefusal.value = null;
    lastFailure.value = false;
    leaseLostWithPendingEdit.value = false;
    clearRetryTimer();
    deps.noteStored(token, document);
  }

  /** A store failed; the pending edit stays, toasts once per outage, and retries. */
  function noteFailed(token: FenceToken): void {
    if (!deps.isCurrent(token)) {
      return;
    }
    if (!lastFailure.value) {
      // One toast per outage: the retry below keeps storing without repeating it.
      toast.failure(AUTOSAVE_FAILURE_COPY);
    }
    lastFailure.value = true;
    leaseLostWithPendingEdit.value = false;
  }

  /** A store was refused; the reason shows until a store succeeds. */
  function noteRefused(token: FenceToken, reason: string): void {
    if (!deps.isCurrent(token)) {
      return;
    }
    lastRefusal.value = reason;
    leaseLostWithPendingEdit.value = false;
  }

  /**
   * A store met `EDIT_LEASE_HELD` with an edit still unconfirmed. The tab
   * turns read-only and keeps that edit visible, so the status leaves
   * `Sparar …` for `Inte sparat` with the lease reason. It promises no
   * retry: while read-only no 5 s retry is scheduled, and the generic retry
   * copy never shows here. A read-only tab with no pending edit keeps
   * today's status. Cleared when the tab takes over again and its edit is
   * stored (`confirmed`) or dropped (the watch below sees no pending edit).
   */
  function noteLeaseLost(): void {
    if (deps.pending()) {
      leaseLostWithPendingEdit.value = true;
    }
  }

  /** A concluded store clears a pinned refusal, failure or lease loss. */
  function clear(): void {
    lastRefusal.value = null;
    lastFailure.value = false;
    leaseLostWithPendingEdit.value = false;
    clearRetryTimer();
  }

  /** True since the last concluded store failed; the next edit stores at once. */
  function hasFailed(): boolean {
    return lastFailure.value;
  }

  /** Rearm the 5 s retry after a failed store; at most one retry waits. */
  function scheduleRetry(flush: () => void): void {
    if (disposed || retryTimer !== null) {
      return;
    }
    retryTimer = setTimeout(() => {
      retryTimer = null;
      flush();
    }, EXAM_WORKSPACE_SAVE_RETRY_MS);
  }

  function dispose(): void {
    disposed = true;
    clearRetryTimer();
  }

  /**
   * The lease-loss pin describes one unstored edit. When the copy no longer
   * differs from the confirmed snapshot without a store succeeding, that
   * edit was dropped: `Ta över` reads the newest state, which replaces it.
   * The pin clears with it, so the status follows the dropped edit to
   * `Sparat` instead of pinning `Inte sparat` past the takeover.
   */
  watch(
    () => deps.pending(),
    (pending) => {
      if (!pending) {
        leaseLostWithPendingEdit.value = false;
      }
    },
  );

  return {
    clear,
    confirmed,
    dispose,
    hasFailed,
    noteFailed,
    noteLeaseLost,
    noteRefused,
    saveStatus,
    saveText,
    scheduleRetry,
  };
}
