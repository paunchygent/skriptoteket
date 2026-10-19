/**
 * Exam workspace save status.
 *
 * Domain purpose:
 *   One computed save status for the one save model (TASK-SKRIPT-40-04-14,
 *   item 6): `Sparar …` while an edit is pending or being stored, `Sparat
 *   HH:MM` once the confirmed snapshot equals the copy in front of the
 *   teacher, and `Inte sparat` with the reason when a store failed or was
 *   refused. A store response never replaces edits made after its snapshot:
 *   the status reads `Sparat` only when the confirmed snapshot equals the
 *   current copy. After a network or server failure the pending edit stays
 *   and the store is retried every 5 s and on the next edit.
 *
 * Relationships:
 *   - Owned by `useExamWorkspaceHistory`, which reports every concluded
 *     store and move through `confirmed`, `noteFailed` and `noteRefused`,
 *     and rearms the retry through `scheduleRetry`.
 *   - The header shows `saveText` with `saveStatus.detail` as its tooltip.
 */

import { computed, ref } from "vue";
import type { ComputedRef } from "vue";

import { isApiError } from "../../../api/client";
import type { NativeExamDocument } from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { examWorkspaceGuestSaveStatus } from "./examWorkspaceGuestDraft";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";

export const AUTOSAVE_FAILURE_COPY = "Ändringen kunde inte sparas som utkast. Försök igen.";

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
  /** A store or a position move confirmed this document; the file holds it now. */
  noteStored: (document: NativeExamDocument) => void;
  /** True while the working copy differs from the confirmed snapshot. */
  pending: () => boolean;
  /** True while a store or a position move is in flight. */
  storing: ComputedRef<boolean>;
};

/**
 * The refusal reason for the status tooltip: the save rule's Swedish copy
 * when the draft itself is refused, the guard's own message when a step
 * changes a placeholder still being converted, else the generic failure copy.
 */
export function refusalReason(snapshot: NativeExamDocument, error: unknown): string {
  const copy = examWorkspaceSaveRefusalCopy(snapshot);
  if (copy !== null) {
    return copy;
  }
  if (
    isApiError(error) &&
    typeof error.details === "object" &&
    error.details !== null &&
    "item_ids" in error.details
  ) {
    return error.message;
  }
  return AUTOSAVE_FAILURE_COPY;
}

export function useExamWorkspaceSaveStatus(deps: ExamWorkspaceSaveStatusDeps) {
  const toast = useToast();
  /** When the last store or move was confirmed, as an ISO timestamp. */
  const lastSavedAt = ref<string | null>(null);
  /** The refusal reason of the last concluded store; null once a store succeeds. */
  const lastRefusal = ref<string | null>(null);
  /** True since the last concluded store failed; cleared once a store succeeds. */
  const lastFailure = ref(false);
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  /**
   * One computed save status: `Sparar …` while an edit is pending or being
   * stored, `Inte sparat` with the reason once a store concluded refused or
   * failed, else `Sparat HH:MM`. A concluded refusal or failure pins
   * `Inte sparat` until a store succeeds, even while newer edits are pending.
   */
  const saveStatus = computed<ExamWorkspaceSaveStatus>(() => {
    if (deps.storing.value) {
      return { state: "saving", detail: null };
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

  function confirmed(document: NativeExamDocument): void {
    lastSavedAt.value = new Date().toISOString();
    lastRefusal.value = null;
    lastFailure.value = false;
    clearRetryTimer();
    deps.noteStored(document);
  }

  /** A store failed; the pending edit stays, toasts once per outage, and retries. */
  function noteFailed(): void {
    if (!lastFailure.value) {
      // One toast per outage: the retry below keeps storing without repeating it.
      toast.failure(AUTOSAVE_FAILURE_COPY);
    }
    lastFailure.value = true;
  }

  /** A store was refused; the reason shows until a store succeeds. */
  function noteRefused(reason: string): void {
    lastRefusal.value = reason;
  }

  /** A concluded store clears a pinned refusal or failure. */
  function clear(): void {
    lastRefusal.value = null;
    lastFailure.value = false;
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

  return {
    clear,
    confirmed,
    dispose,
    hasFailed,
    noteFailed,
    noteRefused,
    saveStatus,
    saveText,
    scheduleRetry,
  };
}
