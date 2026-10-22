/**
 * Exam workspace DOCX import and progressive conversion lifecycle.
 *
 * Domain purpose:
 *   A DOCX import converts in batches. A DigiExam import follows the same
 *   conversion. A QTI .zip is read at once: signed-in into a saved
 *   document, as a guest into the browser draft. Either way it opens like
 *   one from the Öppna list, with no conversion to follow. The server saves a revision when the
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
 *   - Delegates transport to the exam workspace store.
 */

import { onScopeDispose } from "vue";

import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceReplacementTypes";
import { createConversionImportAction } from "./examWorkspaceConversionImportAction";
import type { ExamWorkspaceConversionRuntime } from "./examWorkspaceConversionShared";
import {
  createConversionRuntime,
  stopConversionPolling,
} from "./examWorkspaceConversionShared";
import type { ExamWorkspaceConversionBinding } from "./examWorkspaceConversionShared";
import { createConversionRevisionSync } from "./examWorkspaceConversionRevisionSync";
import { createConversionStatusPoll } from "./examWorkspaceConversionStatusPoll";

export { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./examWorkspaceConversionShared";
export type { ExamWorkspaceConversionBinding } from "./examWorkspaceConversionShared";
export type { ConflictSync } from "./examWorkspaceConversionRevisionSync";
export { serverImportMessage } from "./examWorkspaceConversionImportAction";

export function useExamWorkspaceConversion(
  isBusy: () => boolean,
  binding: ExamWorkspaceConversionBinding,
  /** Opens a saved document by its lineage id, as the Öppna list's open command does. */
  openImported: (lineageId: string) => Promise<ExamWorkspaceRouteOpenOutcome>,
) {
  const runtime: ExamWorkspaceConversionRuntime = createConversionRuntime(binding, openImported);

  function scheduleNext(pollGeneration: number): void {
    void statusPoll.refreshConversion(pollGeneration);
  }

  const revisionSync = createConversionRevisionSync(runtime, scheduleNext);
  const statusPoll = createConversionStatusPoll(
    runtime,
    (status, pollGeneration, duringSave) =>
      revisionSync.applyRevision(status, pollGeneration, duringSave),
  );
  const importAction = createConversionImportAction(
    runtime,
    isBusy,
    (pollGeneration) => statusPoll.refreshConversion(pollGeneration),
  );

  onScopeDispose(() => {
    runtime.poll.generation += 1;
    stopConversionPolling(runtime);
  });

  return {
    conversionError: runtime.conversionError,
    conversionMessage: statusPoll.conversionMessage,
    conversionProgress: statusPoll.conversionProgress,
    adoptConversion: statusPoll.adoptConversion,
    conversionStatus: runtime.conversionStatus,
    convertingItemIds: statusPoll.convertingItemIds,
    importBlocked: importAction.importBlocked,
    importDocument: importAction.importDocument,
    isConverting: runtime.isConverting,
    isEditingConversion: statusPoll.isEditingConversion,
    isImporting: runtime.isImporting,
    retryConversionStatus: statusPoll.retryConversionStatus,
    syncAfterConflict: revisionSync.syncAfterConflict,
  };
}
