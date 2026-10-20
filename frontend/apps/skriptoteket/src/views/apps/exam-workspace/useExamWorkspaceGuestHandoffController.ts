/**
 * Exam workspace guest handoff controller for the signed-in host.
 *
 * Domain purpose:
 *   Run the first handoff attempt for the signed-in host and own every user
 *   message around it. A transient failure renders the view, shows one toast
 *   and retries in the background with doubling delay, at most three times,
 *   cancelled when the scope is disposed; after the last retry fails one more
 *   toast says the next opening tries again. A permanent or vault-full
 *   rejection stops retrying and leaves a notice with download, remove and
 *   (vault-full) manual retry actions. A 401 or superseded sign-in records
 *   nothing and shows nothing. A late success shows a toast and keeps the
 *   open exam; the host navigates only on the first attempt. Removal and
 *   every attempt run inside the shared cross-tab lock and are owned by the
 *   controller's auth lifetime: a retired owner posts, clears and records
 *   nothing, a stale removal never touches another draft's record, and a
 *   stale retry honours a newer draft's record instead of bypassing it.
 *   `lock_unavailable` outcome holds the draft and shows the permanent notice
 *   with download and remove and no retry; remove then runs without the lock,
 *   since that browser has no cross-tab lock to coordinate with. Every attempt
 *   and every removal carries its own abort signal: `pagehide` and scope
 *   disposal abort the current one, while only disposal retires the owner, so
 *   a page restored from the back-forward cache stays live. Aborted attempts
 *   settle without posting, recording or clearing.
 *
 * Relationships:
 *   - Runs `runGuestHandoff` from `useExamWorkspaceGuestHandoff` for every
 *     attempt; reads no storage directly except `clearIf` on remove.
 *   - Owns every handoff toast through `useToast`; `runGuestHandoff` itself
 *     shows no toast.
 *   - Downloads the stored draft record and its stored picture bytes as
 *     one zip through `triggerBrowserDownload`; a missing or unreadable
 *     stored record shows the download failure toast and downloads nothing.
 *   - Called from `ExamWorkspaceTeacherHost.vue` setup; the notice shape is
 *     rendered there by a later unit.
 */

import { onScopeDispose, readonly, shallowRef } from "vue";
import type { Ref } from "vue";

import { useToast } from "../../../composables/useToast";
import { useAuthStore } from "../../../stores/auth";
import { triggerBrowserDownload } from "../../../utils/browserDownload";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import { buildGuestDraftArchive } from "./examWorkspaceGuestDraftArchive";
import { isGuestDraftReadable } from "./examWorkspaceGuestDraftReadability";
import { GuestHandoffLockUnavailableError } from "./examWorkspaceGuestHandoffLock";
import {
  runGuestHandoff,
  type GuestHandoffDeps,
  type GuestHandoffOutcome,
  type GuestHandoffOwner,
} from "./useExamWorkspaceGuestHandoff";
import { EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY } from "./examWorkspaceFileNoticeCopy";

export const GUEST_HANDOFF_RETRY_DELAYS_MS: readonly number[] = [5_000, 10_000, 20_000];

export const GUEST_HANDOFF_TRANSIENT_COPY =
  "Provet från webbläsaren kunde inte flyttas till Mina filer just nu. Det finns kvar i webbläsaren och vi försöker igen om en stund.";
export const GUEST_HANDOFF_LATE_SUCCESS_COPY = "Provet från webbläsaren finns nu i Mina filer.";
export const GUEST_HANDOFF_RETRIES_EXHAUSTED_COPY =
  "Provet kunde inte flyttas till Mina filer. Det finns kvar i webbläsaren. Vi försöker igen nästa gång du öppnar provverktyget.";
export const GUEST_HANDOFF_MANUAL_RETRY_FAILED_COPY =
  "Provet kunde inte flyttas till Mina filer just nu. Försök igen om en stund.";

export type GuestHandoffNotice = { reason: "permanent" | "vault_full" | "unreadable"; busy: boolean };

export type GuestHandoffController = {
  notice: Readonly<Ref<GuestHandoffNotice | null>>;
  start(): Promise<string | null>;
  download(): Promise<void>;
  remove(): Promise<void>;
  retry(): Promise<void>;
};

export function useExamWorkspaceGuestHandoffController(
  deps: Omit<GuestHandoffDeps, "owner">,
  options?: { retryDelaysMs?: readonly number[]; download?: (blob: Blob, filename: string) => void },
): GuestHandoffController {
  const toast = useToast();
  const delays: readonly number[] = options?.retryDelaysMs ?? GUEST_HANDOFF_RETRY_DELAYS_MS;
  const downloadFn: (blob: Blob, filename: string) => void =
    options?.download ?? triggerBrowserDownload;

  const notice = shallowRef<GuestHandoffNotice | null>(null);
  let heldDraft: ExamWorkspaceGuestDraft | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;
  let inFlight = false;
  let currentAttempt: AbortController | null = null;
  let lockUnavailable = false;

  const auth = useAuthStore();
  const session = auth.captureSession();
  const owner: GuestHandoffOwner = {
    isLive: () => !disposed && auth.isCurrentSession(session),
    session,
  };

  /**
   * Map a rejected handoff to the notice reason: vault_full keeps its own
   * notice, a draft the browser itself cannot read shows the unreadable
   * notice, and every other permanent refusal keeps the permanent notice.
   * The browser and the server read the same generated format constants, so
   * an outdated-format refusal only ever arrives for a draft the browser
   * already reports as unreadable.
   */
  function toRejectedNoticeReason(
    reason: "permanent" | "vault_full",
    draft: ExamWorkspaceGuestDraft,
  ): GuestHandoffNotice["reason"] {
    if (reason === "vault_full") {
      return "vault_full";
    }
    if (!isGuestDraftReadable(draft)) {
      return "unreadable";
    }
    return "permanent";
  }

  function abortCurrentAttempt(): void {
    currentAttempt?.abort();
  }

  function onPageHide(): void {
    abortCurrentAttempt();
  }

  if (typeof window !== "undefined") {
    window.addEventListener("pagehide", onPageHide);
  }

  function clearTimer(): void {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function showExhausted(): void {
    toast.warning(GUEST_HANDOFF_RETRIES_EXHAUSTED_COPY);
  }

  function applyBackgroundOutcome(outcome: GuestHandoffOutcome, delayIndex: number): void {
    if (outcome.kind === "handed_off") {
      toast.success(GUEST_HANDOFF_LATE_SUCCESS_COPY);
      return;
    }
    if (outcome.kind === "rejected") {
      heldDraft = outcome.draft;
      notice.value = { reason: toRejectedNoticeReason(outcome.reason, outcome.draft), busy: false };
      return;
    }
    if (outcome.kind === "lock_unavailable") {
      lockUnavailable = true;
      heldDraft = outcome.draft;
      notice.value = { reason: "permanent", busy: false };
      return;
    }
    if (outcome.kind === "transient") {
      if (delayIndex + 1 < delays.length) {
        scheduleBackgroundRetry(delayIndex + 1);
        return;
      }
      showExhausted();
    }
  }

  async function runBackgroundAttempt(delayIndex: number): Promise<void> {
    if (disposed || inFlight) {
      return;
    }
    inFlight = true;
    const attempt = new AbortController();
    currentAttempt = attempt;
    let outcome: GuestHandoffOutcome;
    try {
      outcome = await runGuestHandoff({ ...deps, owner }, { signal: attempt.signal });
    } catch {
      outcome = { kind: "transient" };
    } finally {
      inFlight = false;
    }
    if (disposed) {
      return;
    }
    applyBackgroundOutcome(outcome, delayIndex);
  }

  function scheduleBackgroundRetry(delayIndex: number): void {
    if (disposed) {
      return;
    }
    clearTimer();
    const delayMs = delays[delayIndex];
    if (delayMs === undefined) {
      return;
    }
    timer = setTimeout(() => {
      timer = null;
      void runBackgroundAttempt(delayIndex);
    }, delayMs);
  }

  async function start(): Promise<string | null> {
    if (inFlight) {
      return null;
    }
    inFlight = true;
    const attempt = new AbortController();
    currentAttempt = attempt;
    let outcome: GuestHandoffOutcome;
    try {
      outcome = await runGuestHandoff({ ...deps, owner }, { signal: attempt.signal });
    } catch {
      outcome = { kind: "transient" };
    } finally {
      inFlight = false;
    }
    if (disposed) {
      return null;
    }
    if (outcome.kind === "handed_off") {
      return outcome.lineageId;
    }
    if (outcome.kind === "rejected") {
      heldDraft = outcome.draft;
      notice.value = { reason: toRejectedNoticeReason(outcome.reason, outcome.draft), busy: false };
      return null;
    }
    if (outcome.kind === "lock_unavailable") {
      lockUnavailable = true;
      heldDraft = outcome.draft;
      notice.value = { reason: "permanent", busy: false };
      return null;
    }
    if (outcome.kind === "transient") {
      toast.warning(GUEST_HANDOFF_TRANSIENT_COPY);
      if (delays.length > 0) {
        scheduleBackgroundRetry(0);
      }
      return null;
    }
    return null;
  }

  /**
   * Save the stored draft record and its stored picture bytes as one zip
   * `<titel>.zip` (`draft.json` plus `assets/<id>`), unchanged. A stored
   * draft with another cursor, nothing stored, or any failure downloads
   * nothing and shows the download failure toast. The notice stays busy
   * while the zip is built, as remove does for its own work.
   */
  async function download(): Promise<void> {
    const draft = heldDraft;
    const current = notice.value;
    if (draft === null || current === null) {
      return;
    }
    notice.value = { reason: current.reason, busy: true };
    try {
      const stored = await deps.storage.load();
      if (stored?.draft.cursor !== draft.cursor) {
        toast.failure(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY);
        return;
      }
      const archive = await buildGuestDraftArchive(stored);
      downloadFn(archive.blob, archive.filename);
    } catch {
      toast.failure(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY);
    } finally {
      if (!disposed && notice.value !== null) {
        notice.value = { reason: current.reason, busy: false };
      }
    }
  }

  async function remove(): Promise<void> {
    const draft = heldDraft;
    const current = notice.value;
    if (draft === null || current === null) {
      return;
    }
    notice.value = { reason: current.reason, busy: true };
    const attempt = new AbortController();
    currentAttempt = attempt;
    const body = async (): Promise<boolean> => {
      if (!owner.isLive()) {
        return false;
      }
      await deps.storage.clearIf(draft.cursor);
      if (!owner.isLive()) {
        return false;
      }
      deps.rejections.clearIf(draft.cursor);
      return true;
    };
    let completed = false;
    try {
      if (lockUnavailable) {
        completed = await body();
      } else {
        try {
          completed = await deps.lock.run(body, attempt.signal);
        } catch (lockError: unknown) {
          if (lockError instanceof GuestHandoffLockUnavailableError) {
            lockUnavailable = true;
            completed = await body();
          } else {
            throw lockError;
          }
        }
      }
    } catch {
      if (!disposed) {
        notice.value = { reason: current.reason, busy: false };
      }
      return;
    }
    if (!completed) {
      if (!disposed) {
        notice.value = { reason: current.reason, busy: false };
      }
      return;
    }
    heldDraft = null;
    if (!disposed) {
      notice.value = null;
    }
  }

  async function retry(): Promise<void> {
    const current = notice.value;
    if (current === null || current.busy || inFlight) {
      return;
    }
    notice.value = { reason: current.reason, busy: true };
    inFlight = true;
    const attempt = new AbortController();
    currentAttempt = attempt;
    let outcome: GuestHandoffOutcome;
    try {
      outcome = await runGuestHandoff(
        { ...deps, owner },
        { retryVaultFullOf: heldDraft?.cursor, signal: attempt.signal },
      );
    } catch {
      outcome = { kind: "transient" };
    } finally {
      inFlight = false;
    }
    if (disposed) {
      return;
    }
    if (outcome.kind === "handed_off") {
      heldDraft = null;
      notice.value = null;
      toast.success(GUEST_HANDOFF_LATE_SUCCESS_COPY);
      return;
    }
    if (outcome.kind === "rejected") {
      heldDraft = outcome.draft;
      notice.value = { reason: toRejectedNoticeReason(outcome.reason, outcome.draft), busy: false };
      return;
    }
    if (outcome.kind === "lock_unavailable") {
      lockUnavailable = true;
      heldDraft = outcome.draft;
      notice.value = { reason: "permanent", busy: false };
      return;
    }
    if (outcome.kind === "none") {
      heldDraft = null;
      notice.value = null;
      return;
    }
    if (outcome.kind === "transient") {
      notice.value = { reason: current.reason, busy: false };
      toast.failure(GUEST_HANDOFF_MANUAL_RETRY_FAILED_COPY);
      return;
    }
    notice.value = { reason: current.reason, busy: false };
  }

  onScopeDispose(() => {
    disposed = true;
    abortCurrentAttempt();
    if (typeof window !== "undefined") {
      window.removeEventListener("pagehide", onPageHide);
    }
    clearTimer();
  });

  return {
    download,
    notice: readonly(notice),
    remove,
    retry,
    start,
  };
}
