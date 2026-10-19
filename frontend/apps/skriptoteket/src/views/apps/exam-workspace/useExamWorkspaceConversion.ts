/**
 * Exam workspace DOCX import and progressive conversion lifecycle.
 *
 * Domain purpose:
 *   A DOCX import converts in batches. A DigiExam import follows the same
 *   conversion. A QTI .zip import is read at once into a saved document and
 *   opens like one from the Öppna list, with no conversion to follow. The
 *   server saves a revision when the
 *   first batch is ready, with placeholders for the questions still
 *   converting, and a new revision for each later batch. Every document
 *   response names the import that created its lineage, read under the same
 *   lock as the document, and `adoptConversion` takes it from each response
 *   the open copy stands on: an unfinished conversion is followed, whichever
 *   browser started it and however the exam was opened. Following polls the
 *   conversion and merges every newer revision into the teacher's copy: each
 *   batch replaces its own placeholders, and the teacher's edits of converted
 *   items are kept. Placeholders of the open copy stay locked, and the import
 *   is reported done, only once the open copy holds the final revision.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceDocument`, which hands over its document refs
 *     through `ExamWorkspaceConversionBinding`.
 *   - Merges with `mergeConversionRevision` (client twin of the server merge).
 *   - Delegates transport to `api/examWorkspace.ts`.
 */

import { computed, onScopeDispose, ref } from "vue";
import type { Ref } from "vue";

import { isApiError } from "../../../api/client";
import {
  getExamWorkspaceConversionStatus,
  getExamWorkspaceDocument,
  importExamWorkspaceDigiExam,
  importExamWorkspaceDocument as requestImportExamWorkspaceDocument,
  importExamWorkspaceQti,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceConversionUnit,
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useAiAccess } from "../../../composables/useAiAccess";
import { useToast } from "../../../composables/useToast";
import { mergeConversionRevision } from "./examWorkspaceConversionMerge";

export const EXAM_WORKSPACE_CONVERSION_POLL_MS = 3000;
const CONVERSION_MAX_POLL_MS = 30_000;
const STATUS_FAILURE_COPY = "Det gick inte att hämta konverteringen eller öppna provet. Försöker igen …";
const IMPORT_FAILURE_COPY = "Det gick inte att läsa in provet. Försök igen.";

/** A DigiExam export (.dxe) is read by its own importer and stays open to every role. */
function isDigiExamFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".dxe");
}

/** A QTI package (.zip) is read without AI and stays open to every role. */
function isQtiPackageFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".zip");
}

/** The document owner's state that conversion revisions are applied to. */
export type ExamWorkspaceConversionBinding = {
  isDirty: Readonly<Ref<boolean>>;
  /** The server document the local copy started from. */
  serverDocument: Ref<NativeExamDocument | null>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  workspaceDocument: Ref<NativeExamDocument | null>;
  /** Capture metadata ordering before a GET; reconcile without delaying its application. */
  beginDocumentRead: () => (response: ExamWorkspaceDocumentResponse) => ExamWorkspaceDocumentResponse;
  /** Replace the local copy with a server response; `local` keeps merged teacher edits. */
  applyResponse: (response: ExamWorkspaceDocumentResponse, local?: NativeExamDocument) => void;
  /** Called once before the first revision of a new import is shown. */
  beforeFirstRevision: () => void;
  /** A save is in flight; its response replaces the copy, so merging waits. */
  isSaving: () => boolean;
};

/** What a save conflict turned out to be, once the conversion revision was checked. */
export type ConflictSync = "merged" | "unrelated" | "unknown";

export function useExamWorkspaceConversion(
  isBusy: () => boolean,
  binding: ExamWorkspaceConversionBinding,
  /** Opens a saved document by its lineage id, as the Öppna list's open command does. */
  openImported: (lineageId: string) => Promise<boolean>,
) {
  const toast = useToast();
  const { canUseAi } = useAiAccess();
  const isImporting = ref(false);
  const conversionStatus = ref<ExamWorkspaceConversionStatus | null>(null);
  const isConverting = ref(false);
  const conversionError = ref<string | null>(null);
  /**
   * The one rule for every import path (picker, drop, `importDocument`): no
   * import while the workspace is busy or the open exam has unsaved changes,
   * which the new exam would discard.
   */
  const importBlocked = computed(() => isBusy() || binding.isDirty.value);
  /** Units of `binding.serverDocument` while its conversion runs; null otherwise. */
  const shownUnits = ref<ExamWorkspaceConversionUnit[] | null>(null);
  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let generation = 0;
  let pollFailures = 0;
  /** The one status request in flight (poll or conflict sync); a second waits for it. */
  let statusRequest: Promise<void> | null = null;

  const conversionProgress = computed(() => {
    const status = conversionStatus.value;
    if (!isConverting.value || !status || status.questions_total === 0) return null;
    return { done: status.questions_done, total: status.questions_total };
  });

  const conversionMessage = computed(() => {
    const progress = conversionProgress.value;
    if (progress) {
      return `Konverterar provet: ${progress.done} av ${progress.total} frågor klara.`;
    }
    if (isConverting.value) return "Konverterar provet …";
    if (conversionStatus.value?.state === "failed") {
      return conversionStatus.value.error_message ?? IMPORT_FAILURE_COPY;
    }
    return conversionError.value;
  });

  /** The open document is the followed import's, so the teacher may edit it while batches arrive. */
  const isEditingConversion = computed(
    () =>
      shownUnits.value !== null &&
      binding.summary.value?.lineage_id === conversionStatus.value?.lineage_id,
  );

  /**
   * Placeholders of the revision the open copy stands on. A newer status can
   * arrive while its revision waits for an in-flight save, so a placeholder
   * stays locked until its batch is merged into the open copy.
   */
  const convertingItemIds = computed<ReadonlySet<string>>(() => {
    if (!isEditingConversion.value) return new Set();
    return new Set(
      (shownUnits.value ?? [])
        .filter((unit) => unit.state === "converting")
        .flatMap((unit) => unit.item_ids),
    );
  });

  function stopPolling(): void {
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function schedulePoll(pollGeneration: number): void {
    stopPolling();
    const delay = Math.min(
      EXAM_WORKSPACE_CONVERSION_POLL_MS * 2 ** Math.max(0, pollFailures - 1),
      CONVERSION_MAX_POLL_MS,
    );
    pollTimer = setTimeout(() => {
      pollTimer = null;
      void refreshConversion(pollGeneration);
    }, delay);
  }

  function isFinished(status: ExamWorkspaceConversionStatus): boolean {
    return status.state === "succeeded" || status.state === "failed";
  }

  /** The open copy stands on the status's revision or a later one, so it holds its results. */
  function holdsRevision(status: ExamWorkspaceConversionStatus): boolean {
    const revision = status.document_revision;
    return (
      revision === null ||
      (binding.summary.value?.lineage_id === status.lineage_id &&
        binding.summary.value.version >= revision)
    );
  }

  function finish(status: ExamWorkspaceConversionStatus): void {
    conversionStatus.value = status;
    isConverting.value = false;
    shownUnits.value = null;
    conversionError.value = null;
    // The opened exam is the success state; toasts report failures only (user rule 2026-10-17).
    stopPolling();
  }

  /**
   * Take the conversion state of a server response the open copy now stands
   * on. Its units name exactly the placeholders that revision holds, so they
   * become the lock. An unfinished conversion is followed; a finished one
   * means the response holds every result, so following ends.
   */
  function adoptConversion(response: ExamWorkspaceDocumentResponse): void {
    const conversion = response.conversion;
    const following =
      isConverting.value && conversion !== null && conversionStatus.value?.job_id === conversion.job_id;
    if (conversion !== null && !isFinished(conversion)) {
      shownUnits.value = conversion.units;
      // While following, the poll owns the status: a save response can carry an older one.
      if (!following) {
        conversionStatus.value = conversion;
        generation += 1;
        isConverting.value = true;
        conversionError.value = null;
        pollFailures = 0;
        schedulePoll(generation);
      }
      return;
    }
    if (following) {
      finish(conversion);
      return;
    }
    if (isConverting.value) {
      // The teacher opened another exam: its conversion is followed again when reopened.
      generation += 1;
      isConverting.value = false;
      stopPolling();
    }
    shownUnits.value = null;
    conversionStatus.value = null;
    conversionError.value = null;
  }

  /**
   * Show a newer revision of the followed import's exam. The first one
   * replaces the open exam; a later one is merged into the teacher's copy
   * with the units its own response names, so a later revision another tab
   * saved on top of the conversion's merges the same way. Returns true when a
   * newer revision waits for an in-flight save, so the caller polls again
   * before finishing. A fetched revision without its conversion throws like a
   * failed fetch: the copy, its lock and the shown units stay as they are.
   */
  async function applyRevision(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
    duringSave = false,
  ): Promise<boolean> {
    if (status.document_revision === null || holdsRevision(status)) return false;
    if (binding.isSaving() && !duringSave) return true;
    const first = binding.summary.value?.lineage_id !== status.lineage_id;
    const shown = shownUnits.value ?? [];
    const reconcile = binding.beginDocumentRead();
    const response = reconcile(await getExamWorkspaceDocument(status.lineage_id));
    if (pollGeneration !== generation) return false;
    const conversion = response.conversion;
    if (conversion === null) {
      // Only the response's own conversion names the units of its head: reconcile like a failed fetch.
      throw new Error("The followed exam's revision came without its conversion.");
    }
    const local = binding.workspaceDocument.value;
    const base = binding.serverDocument.value;
    if (first) {
      binding.beforeFirstRevision();
      binding.applyResponse(response);
    } else if (!binding.isDirty.value || !local || !base) {
      binding.applyResponse(response);
    } else {
      const merged = mergeConversionRevision({
        base,
        baseUnits: shown,
        head: response.document,
        headUnits: conversion.units,
        local,
      });
      binding.applyResponse(response, merged);
    }
    return false;
  }

  async function applyConversionStatus(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
  ): Promise<void> {
    if (pollGeneration !== generation) return;
    conversionStatus.value = status;
    const deferred = await applyRevision(status, pollGeneration);
    // Adopting the fetched revision may already have ended or replaced this poll chain.
    if (pollGeneration !== generation || !isConverting.value) return;
    if (deferred || !holdsRevision(status)) {
      schedulePoll(pollGeneration);
    } else if (isFinished(status)) {
      finish(status);
    } else {
      pollFailures = 0;
      schedulePoll(pollGeneration);
    }
  }

  async function runStatusRequest(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
  ): Promise<void> {
    try {
      const next = isFinished(status)
        ? status
        : await getExamWorkspaceConversionStatus(status.job_id);
      await applyConversionStatus(next, pollGeneration);
      if (pollGeneration === generation) {
        pollFailures = 0;
        conversionError.value = null;
      }
    } catch {
      if (pollGeneration !== generation) return;
      conversionError.value = STATUS_FAILURE_COPY;
      pollFailures += 1;
      schedulePoll(pollGeneration);
    }
  }

  async function refreshConversion(pollGeneration: number): Promise<void> {
    const status = conversionStatus.value;
    if (!status || statusRequest || !isConverting.value) return;
    const request = runStatusRequest(status, pollGeneration).finally(() => {
      statusRequest = null;
    });
    statusRequest = request;
    await request;
  }

  function retryConversionStatus(): void {
    stopPolling();
    void refreshConversion(generation);
  }

  /**
   * After a save conflict on the converting exam, merge the revision
   * conversion wrote meanwhile, waiting for a status request already in
   * flight first. Returns "merged" when the open copy now stands on a newer
   * revision than the failed save expected, so the caller can save again
   * without losing edits; "unrelated" when conversion wrote no revision newer
   * than the failed save's; and "unknown" when conversion did but it could not
   * be merged (the fetch failed or came without its conversion), so the caller keeps the teacher's copy and
   * the next poll merges it. Outside conversion it returns "unrelated".
   */
  async function syncAfterConflict(expectedRevision: number): Promise<ConflictSync> {
    const pollGeneration = generation;
    while (statusRequest) await statusRequest;
    const status = conversionStatus.value;
    if (pollGeneration !== generation || !status || !isEditingConversion.value) {
      return "unrelated";
    }
    let conversionRevision = 0;
    const request = (async () => {
      const next = await getExamWorkspaceConversionStatus(status.job_id);
      if (pollGeneration !== generation) return;
      conversionStatus.value = next;
      conversionRevision = next.document_revision ?? 0;
      await applyRevision(next, pollGeneration, true);
    })().finally(() => {
      statusRequest = null;
    });
    statusRequest = request;
    try {
      await request;
    } catch {
      return "unknown";
    }
    if (pollGeneration !== generation) return "unknown";
    // The poll chain may have found this request pending and ended; resume it.
    if (isConverting.value && pollTimer === null) schedulePoll(pollGeneration);
    if ((binding.summary.value?.version ?? 0) > expectedRevision) return "merged";
    return conversionRevision > expectedRevision ? "unknown" : "unrelated";
  }

  /**
   * The server's Swedish refusal of an import, or null when the failure
   * carries no server message to show (the generic 422 envelope or an
   * HTTP-level fault).
   */
  function serverImportMessage(error: unknown): string | null {
    return isApiError(error) && error.code !== "HTTP_ERROR" && error.message !== "Validation error"
      ? error.message
      : null;
  }

  async function importDocument(file: File, courseKey: string | null): Promise<void> {
    if (importBlocked.value || isConverting.value) return;
    // A Word import is a paid AI conversion and stays admin-only until the spend cap ships;
    // the Öppna drawer already shows the L3 note for the refused file.
    if (!isDigiExamFile(file) && !isQtiPackageFile(file) && !canUseAi.value) return;
    const pollGeneration = ++generation;
    isImporting.value = true;
    conversionError.value = null;
    conversionStatus.value = null;
    shownUnits.value = null;
    pollFailures = 0;
    try {
      // A QTI package (.zip) is read at once into a saved document: no
      // conversion follows, and the saved exam opens through the same
      // `openDocument` path the Öppna list's open command uses.
      if (isQtiPackageFile(file)) {
        const summary = await importExamWorkspaceQti(file, courseKey);
        if (pollGeneration !== generation) return;
        // `openImported` refuses while this import still counts as busy.
        isImporting.value = false;
        await openImported(summary.lineage_id);
        return;
      }
      // A DigiExam export (.dxe) is read by its own importer; both follow the same conversion.
      const request = isDigiExamFile(file)
        ? importExamWorkspaceDigiExam
        : requestImportExamWorkspaceDocument;
      const status = await request(file, courseKey);
      if (pollGeneration !== generation) return;
      isConverting.value = true;
      conversionStatus.value = status;
      await refreshConversion(pollGeneration);
    } catch (error) {
      if (pollGeneration !== generation) return;
      const message = serverImportMessage(error) ?? IMPORT_FAILURE_COPY;
      conversionError.value = message;
      toast.failure(message);
    } finally {
      isImporting.value = false;
    }
  }

  onScopeDispose(() => {
    generation += 1;
    stopPolling();
  });

  return {
    conversionError,
    conversionMessage,
    conversionProgress,
    adoptConversion,
    conversionStatus,
    convertingItemIds,
    importBlocked,
    importDocument,
    isConverting,
    isEditingConversion,
    isImporting,
    retryConversionStatus,
    syncAfterConflict,
  };
}
