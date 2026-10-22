/**
 * Exam workspace conversion import action.
 *
 * Domain purpose:
 *   Enter one DOCX, PDF, DigiExam or QTI import. A DOCX import converts in
 *   batches; a DigiExam import follows the same conversion. A QTI .zip is
 *   read at once: signed-in into a saved document, as a guest into the
 *   browser draft. The server saves a revision when the first batch is ready,
 *   with placeholders for the questions still converting. The door's daily
 *   limit stops Word imports for the page session with its own inline note.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceConversion` through the shared conversion
 *     runtime; the status poll is injected so the import never owns the timer.
 *   - Merges with `mergeConversionRevision` (client twin of the server merge).
 *   - Delegates transport to the exam workspace store.
 */

import { computed } from "vue";

import { isApiError } from "../../../api/client";
import { useAiAccess } from "../../../composables/useAiAccess";
import { useToast } from "../../../composables/useToast";
import {
  aiDailyLimitFor,
  aiLimitFromError,
  aiTryAgainFromError,
  aiLimitFromStatus,
  aiLimitNote,
  markAiDailyLimit,
} from "../../../composables/aiDailyLimit";
import type { ExamWorkspaceConversionRuntime } from "./examWorkspaceConversionShared";
import { IMPORT_FAILURE_COPY } from "./examWorkspaceConversionShared";
import {
  importQtiPackage,
  isDigiExamFile,
  isQtiPackageFile,
} from "./examWorkspaceConversionImport";

/**
 * The server's Swedish refusal of an import, or null when the failure
 * carries no server message to show (the generic 422 envelope or an
 * HTTP-level fault). Shared with the new-exam flow, whose create failure
 * follows the same message rule.
 */
export function serverImportMessage(error: unknown): string | null {
  return isApiError(error) && error.code !== "HTTP_ERROR" && error.message !== "Validation error"
    ? error.message
    : null;
}

export function createConversionImportAction(
  runtime: ExamWorkspaceConversionRuntime,
  isBusy: () => boolean,
  refreshConversion: (pollGeneration: number) => Promise<void>,
) {
  const { binding } = runtime;
  const toast = useToast();
  const { canUseAi } = useAiAccess();
  const smallAllowance = aiDailyLimitFor("small");

  /**
   * The one rule for every import path (picker, drop, `importDocument`): no
   * import while the workspace is busy or the open exam has unsaved changes,
   * which the new exam would discard.
   */
  const importBlocked = computed(() => isBusy() || binding.isDirty.value);

  async function importDocument(file: File, courseKey: string | null): Promise<void> {
    if (importBlocked.value || runtime.isConverting.value) return;
    // A Word or PDF import is a paid AI conversion and stays admin-only until the spend cap ships;
    // the Öppna drawer already shows the L3 note for the refused file.
    if (!isDigiExamFile(file) && !isQtiPackageFile(file) && !canUseAi.value) return;
    // The door's daily limit stops Word imports for the page session; the
    // Öppna drawer names the limit next to the import instead.
    if (!isDigiExamFile(file) && !isQtiPackageFile(file) && smallAllowance.reached.value) {
      runtime.conversionError.value = smallAllowance.note.value ?? aiLimitNote("pool");
      return;
    }
    const pollGeneration = ++runtime.poll.generation;
    runtime.isImporting.value = true;
    runtime.conversionError.value = null;
    runtime.conversionStatus.value = null;
    runtime.shownUnits.value = null;
    runtime.poll.failures = 0;
    try {
      // A QTI package (.zip) is read at once: signed-in it becomes a saved
      // document, as a guest it becomes the browser draft. Either way the
      // exam opens through the same `openDocument` path the Öppna list's
      // open command uses, and no conversion follows.
      if (isQtiPackageFile(file)) {
        // The guest slot write is admitted only while this import is still
        // the current one and the sync gate generation it started in is
        // still current: a later import, the scope's disposal, a lost lease
        // or pagehide retires it before its late parse can replace the
        // retained draft, and a lease that frees or expires afterwards does
        // not revive it.
        const authority = binding.getFence().begin();
        const lineageId = await importQtiPackage(binding.store, file, courseKey, {
          isLive: () => pollGeneration === runtime.poll.generation && binding.isCurrent(authority),
          tabId: binding.tabId(),
        });
        if (pollGeneration !== runtime.poll.generation || lineageId === null) return;
        binding.noteImportStarted(lineageId);
        // `openImported` refuses while this import still counts as busy.
        runtime.isImporting.value = false;
        await runtime.openImported(lineageId);
        return;
      }
      const teacher = binding.store.teacher;
      if (!teacher) return;
      // A DigiExam export (.dxe) is read by its own importer; both follow the same conversion.
      const request = isDigiExamFile(file)
        ? teacher.importExamWorkspaceDigiExam
        : teacher.importExamWorkspaceDocument;
      const status = await request(file, courseKey);
      if (pollGeneration !== runtime.poll.generation) return;
      const limit = aiLimitFromStatus(status);
      if (limit !== null) {
        markAiDailyLimit("small", limit);
      }
      binding.noteImportStarted(status.lineage_id);
      runtime.isConverting.value = true;
      runtime.conversionStatus.value = status;
      await refreshConversion(pollGeneration);
    } catch (error) {
      if (pollGeneration !== runtime.poll.generation) return;
      // No toast for the door's limit: the Öppna drawer names it inline.
      const limit = aiLimitFromError(error);
      if (limit !== null) {
        markAiDailyLimit("small", limit);
        runtime.conversionError.value = aiLimitNote(limit);
        return;
      }
      // The busy door never disables the import: its sentence stands inline
      // without a toast and the next import attempt clears it.
      const tryAgain = aiTryAgainFromError(error);
      if (tryAgain !== null) {
        runtime.conversionError.value = tryAgain;
        return;
      }
      const message = serverImportMessage(error) ?? IMPORT_FAILURE_COPY;
      runtime.conversionError.value = message;
      toast.failure(message);
    } finally {
      runtime.isImporting.value = false;
    }
  }

  return { importBlocked, importDocument };
}
