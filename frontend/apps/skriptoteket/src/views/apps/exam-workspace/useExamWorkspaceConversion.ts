/**
 * Exam workspace DOCX import and progressive conversion lifecycle.
 *
 * Domain purpose:
 *   A DOCX import converts in batches. The server saves a revision when the
 *   first batch is ready, with placeholders for the questions still
 *   converting, and a new revision for each later batch. This composable
 *   polls the conversion, opens the first revision, and merges every later
 *   revision into the teacher's copy: each batch replaces its own
 *   placeholders, and the teacher's edits of converted items are kept. It
 *   also reports progress and which items are still placeholders in the open
 *   copy; those stay locked until their batch is merged into it.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceDocument`, which hands over its document refs
 *     through `ExamWorkspaceConversionBinding`.
 *   - Merges with `mergeConversionRevision` (client twin of the server merge).
 *   - Delegates transport to `api/examWorkspace.ts`.
 */

import { computed, onScopeDispose, ref } from "vue";
import type { Ref } from "vue";

import {
  getExamWorkspaceConversionStatus,
  getExamWorkspaceDocument,
  importExamWorkspaceDocument as requestImportExamWorkspaceDocument,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceConversionUnit,
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { mergeConversionRevision } from "./examWorkspaceConversionMerge";

export const EXAM_WORKSPACE_CONVERSION_POLL_MS = 3000;
const CONVERSION_MAX_POLL_MS = 30_000;
const STATUS_FAILURE_COPY = "Det gick inte att hämta konverteringen eller öppna provet. Försöker igen …";
const IMPORT_FAILURE_COPY = "Det gick inte att läsa in provet. Försök igen.";
const IMPORT_SUCCESS_COPY = "Provet är inläst.";

/** The document owner's state that conversion revisions are applied to. */
export type ExamWorkspaceConversionBinding = {
  isDirty: Ref<boolean>;
  /** The server document the local copy started from. */
  serverDocument: Ref<NativeExamDocument | null>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  workspaceDocument: Ref<NativeExamDocument | null>;
  /** Replace the local copy with a server response; `local` keeps merged teacher edits. */
  applyResponse: (
    response: ExamWorkspaceDocumentResponse,
    local?: NativeExamDocument,
    dirty?: boolean,
  ) => void;
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
) {
  const toast = useToast();
  const isImporting = ref(false);
  const conversionStatus = ref<ExamWorkspaceConversionStatus | null>(null);
  const isConverting = ref(false);
  const conversionError = ref<string | null>(null);
  /** Units as of `binding.serverDocument`; null until this import's first revision is shown. */
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

  /** The open document is this import's, so the teacher may edit it while batches arrive. */
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
    if (!isConverting.value || !isEditingConversion.value) return new Set();
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

  /**
   * Show a newer conversion revision. The first one replaces the open exam; a
   * later one is merged into the teacher's copy. A revision is applied only
   * when the head still is the revision the status describes, so the units
   * always match the document they index. Returns true when a newer revision
   * waits for an in-flight save, so the caller polls again before finishing.
   */
  async function applyRevision(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
    duringSave = false,
  ): Promise<boolean> {
    const revision = status.document_revision;
    if (revision === null) return false;
    const first = shownUnits.value === null;
    if (!first && binding.summary.value?.lineage_id !== status.lineage_id) return false;
    if (!first && (binding.summary.value?.version ?? 0) >= revision) return false;
    if (binding.isSaving() && !duringSave) return true;
    const response = await getExamWorkspaceDocument(status.lineage_id);
    if (pollGeneration !== generation || response.summary.version !== revision) return false;
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
        baseUnits: shownUnits.value ?? [],
        head: response.document,
        headUnits: status.units,
        local,
      });
      binding.applyResponse(response, merged.document, merged.teacherEditsKept);
    }
    shownUnits.value = status.units;
    return false;
  }

  async function applyConversionStatus(
    status: ExamWorkspaceConversionStatus,
    pollGeneration: number,
  ): Promise<void> {
    if (pollGeneration !== generation) return;
    conversionStatus.value = status;
    const deferred = await applyRevision(status, pollGeneration);
    if (pollGeneration !== generation) return;
    if (deferred) {
      schedulePoll(pollGeneration);
    } else if (status.state === "failed") {
      isConverting.value = false;
      conversionError.value = null;
      stopPolling();
    } else if (status.state === "succeeded") {
      isConverting.value = false;
      conversionError.value = null;
      stopPolling();
      toast.success(IMPORT_SUCCESS_COPY);
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
      const next = status.state === "succeeded" || status.state === "failed"
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
   * be merged (the fetch failed, or a later batch moved the head past the
   * status), so the caller keeps the teacher's copy and the next poll merges
   * it. Outside conversion it returns "unrelated".
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

  async function importDocument(file: File): Promise<void> {
    if (isBusy() || isConverting.value) return;
    const pollGeneration = ++generation;
    isImporting.value = true;
    conversionError.value = null;
    conversionStatus.value = null;
    shownUnits.value = null;
    pollFailures = 0;
    try {
      const status = await requestImportExamWorkspaceDocument(file);
      if (pollGeneration !== generation) return;
      isConverting.value = true;
      conversionStatus.value = status;
      await refreshConversion(pollGeneration);
    } catch {
      if (pollGeneration !== generation) return;
      conversionError.value = IMPORT_FAILURE_COPY;
      toast.failure(IMPORT_FAILURE_COPY);
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
    conversionStatus,
    convertingItemIds,
    importDocument,
    isConverting,
    isEditingConversion,
    isImporting,
    retryConversionStatus,
    syncAfterConflict,
  };
}
