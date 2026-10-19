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
 *   open exam; the host navigates only on the first attempt.
 *
 * Relationships:
 *   - Runs `runGuestHandoff` from `useExamWorkspaceGuestHandoff` for every
 *     attempt; reads no storage directly except `clearIf` on remove.
 *   - Owns every handoff toast through `useToast`; `runGuestHandoff` itself
 *     shows no toast.
 *   - Downloads the held rejected draft as JSON through
 *     `triggerBrowserDownload`.
 *   - Called from `ExamWorkspaceTeacherHost.vue` setup; the notice shape is
 *     rendered there by a later unit.
 */

import { onScopeDispose, readonly, shallowRef } from "vue";
import type { Ref } from "vue";

import { useToast } from "../../../composables/useToast";
import { triggerBrowserDownload } from "../../../utils/browserDownload";
import type { ExamWorkspaceGuestDraft } from "./examWorkspaceGuestDraft";
import {
  runGuestHandoff,
  type GuestHandoffDeps,
  type GuestHandoffOutcome,
} from "./useExamWorkspaceGuestHandoff";

export const GUEST_HANDOFF_RETRY_DELAYS_MS: readonly number[] = [5_000, 10_000, 20_000];

export const GUEST_HANDOFF_TRANSIENT_COPY =
  "Provet från webbläsaren kunde inte flyttas till Mina filer just nu. Det finns kvar i webbläsaren och vi försöker igen om en stund.";
export const GUEST_HANDOFF_LATE_SUCCESS_COPY = "Provet från webbläsaren finns nu i Mina filer.";
export const GUEST_HANDOFF_RETRIES_EXHAUSTED_COPY =
  "Provet från webbläsaren kunde inte flyttas till Mina filer. Det finns kvar i webbläsaren och flyttas nästa gång du öppnar provverktyget.";
export const GUEST_HANDOFF_MANUAL_RETRY_FAILED_COPY =
  "Det gick inte att nå Mina filer just nu. Försök igen om en stund.";

export type GuestHandoffNotice = { reason: "permanent" | "vault_full"; busy: boolean };

export type GuestHandoffController = {
  notice: Readonly<Ref<GuestHandoffNotice | null>>;
  start(): Promise<string | null>;
  download(): void;
  remove(): Promise<void>;
  retry(): Promise<void>;
};

export function useExamWorkspaceGuestHandoffController(
  deps: GuestHandoffDeps,
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
      notice.value = { reason: outcome.reason, busy: false };
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
    let outcome: GuestHandoffOutcome;
    try {
      outcome = await runGuestHandoff(deps);
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
    let outcome: GuestHandoffOutcome;
    try {
      outcome = await runGuestHandoff(deps);
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
      notice.value = { reason: outcome.reason, busy: false };
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

  function download(): void {
    if (heldDraft === null) {
      return;
    }
    const draft = heldDraft;
    const title = draft.saved_document.title.trim();
    const filename = `${title === "" ? "Prov" : title}.json`;
    downloadFn(new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" }), filename);
  }

  async function remove(): Promise<void> {
    const draft = heldDraft;
    const current = notice.value;
    if (draft === null || current === null) {
      return;
    }
    notice.value = { reason: current.reason, busy: true };
    try {
      // True or false both close the notice: false means a newer draft owns
      // the slot now and is handed off on the next load.
      await deps.storage.clearIf(draft.cursor);
    } catch {
      if (!disposed) {
        notice.value = { reason: current.reason, busy: false };
      }
      return;
    }
    deps.rejections.clear();
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
    let outcome: GuestHandoffOutcome;
    try {
      outcome = await runGuestHandoff(deps, { ignoreRecordedRejection: true });
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
      notice.value = { reason: outcome.reason, busy: false };
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
