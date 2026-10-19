/**
 * Exam workspace saving.
 *
 * Domain purpose:
 *   Overwrite the exam file with Spara, store the working copy as a new exam
 *   with Spara som, refuse a Spara the server would reject with Swedish copy
 *   naming the questions, merge a batch saved meanwhile and save again, and
 *   recover from a stale-save conflict by reloading the newest revision.
 *
 * Relationships:
 *   - Transport through the exam workspace store.
 *   - Installs each response through the document's `applyResponse`; reads go
 *     through its `beginDocumentRead` so renames stay reconciled.
 *   - Conversion merges come from `useExamWorkspaceConversion` (`syncAfterConflict`);
 *     AI suggestion and gap keying replays run through `arrivals` and `keying`.
 *   - Marks the shared operation busy flag while a request runs.
 */

import { ref } from "vue";
import type { ComputedRef, Ref } from "vue";

import { isApiError } from "../../../api/client";
import type { ApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import type { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";
import type { useExamWorkspaceGapKeying } from "./useExamWorkspaceGapKeying";
import type { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";

export const EXAM_WORKSPACE_CONFLICT_COPY =
  "Det gick inte att spara eftersom provet ändrades någon annanstans. Den senaste sparade versionen har lästs in på nytt.";

export const RELOAD_FAILURE_COPY = "Det gick inte att läsa in provet på nytt. Försök igen.";
const SAVE_FAILURE_COPY = "Det gick inte att spara provet. Försök igen.";
const SAVE_AS_FAILURE_COPY = "Det gick inte att spara en kopia av provet. Försök igen.";

export type ExamWorkspaceSaveAsOutcome = "saved" | "name_taken" | "failed";

type SaveState = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  isBusy: ComputedRef<boolean>;
  operationBusy: Ref<boolean>;
  applyResponse: (response: ExamWorkspaceDocumentResponse) => void;
  beginDocumentRead: () => (response: ExamWorkspaceDocumentResponse) => ExamWorkspaceDocumentResponse;
  syncAfterConflict: ReturnType<typeof useExamWorkspaceConversion>["syncAfterConflict"];
  arrivals: ReturnType<typeof useExamWorkspaceSaveArrivals>;
  keying: ReturnType<typeof useExamWorkspaceGapKeying>;
  /** The store the save reads and writes run through. */
  store: ExamWorkspaceStore;
};

function nameInUse(error: unknown): boolean {
  if (!isApiError(error) || error.status !== 422) {
    return false;
  }
  const details = error.details;
  return (
    typeof details === "object" &&
    details !== null &&
    "code" in details &&
    details.code === "vault_name_in_use"
  );
}

/** A save refused because it changed questions that still convert (D30). */
function refusedPlaceholderChange(error: unknown): error is ApiError {
  return (
    isApiError(error) &&
    error.status === 422 &&
    typeof error.details === "object" &&
    error.details !== null &&
    "item_ids" in error.details
  );
}

export function useExamWorkspaceSave(state: SaveState) {
  const toast = useToast();
  const { arrivals, keying, operationBusy, summary, workspaceDocument } = state;
  const conflictNotice = ref<string | null>(null);

  /** Returns whether the reloaded revision replaced the teacher's copy. */
  async function reloadAfterConflict(lineageId: string): Promise<boolean> {
    try {
      const reconcile = state.beginDocumentRead();
      const response = reconcile(await state.store.shared.getExamWorkspaceDocument(lineageId));
      state.applyResponse(response);
      keying.invalidateCopy();
      return true;
    } catch {
      toast.failure(RELOAD_FAILURE_COPY);
      return false;
    }
  }

  /** Spara at `positionStepId`, the history snapshot the editor stands on (null: history unread). */
  async function saveDocument(
    positionStepId: string | null,
    afterConversionConflict = false,
  ): Promise<boolean> {
    const current = workspaceDocument.value;
    const currentSummary = summary.value;
    if (!current || !currentSummary || (state.isBusy.value && !afterConversionConflict)) {
      return false;
    }
    if (positionStepId === null) {
      // Without the editor's position the server cannot keep the saved copy in its history.
      toast.failure(SAVE_FAILURE_COPY);
      return false;
    }
    const refusalCopy = examWorkspaceSaveRefusalCopy(current.items);
    if (refusalCopy) {
      toast.failure(refusalCopy);
      return false;
    }
    const expectedRevision = current.revision;
    const payload: NativeExamDocument = { ...current, revision: expectedRevision + 1 };
    const payloadMark = arrivals.payloadMark();
    const openedArrivals = arrivals.beginHold();
    const keyingMark = keying.payloadMark();
    const openedKeying = keying.beginHold();
    operationBusy.value = true;
    try {
      const response = await state.store.shared.saveExamWorkspaceDocument(currentSummary.lineage_id, {
        document: payload,
        expectedRevision,
        positionStepId,
      });
      state.applyResponse(response);
      // The response holds the payload; arrivals that landed after it was read run again on it.
      arrivals.replayAfterResponse(payloadMark);
      // The response holds the payload; spellings merged in after it was read run again on it.
      keying.replayAfterResponse(keyingMark);
      // "Sparat HH:MM" in the header is the success state; toasts report failures only.
      conflictNotice.value = null;
      return true;
    } catch (error) {
      // A batch saved meanwhile: merge it and save again on top of it. Each
      // retry stands on a strictly newer revision, so batches bound the loop.
      const conflict = isApiError(error) && error.status === 409;
      const sync = conflict ? await state.syncAfterConflict(expectedRevision) : "unrelated";
      if (sync === "merged") {
        return await saveDocument(positionStepId, true);
      }
      if (refusedPlaceholderChange(error)) {
        // The server names the converting questions the save changed; the copy stays.
        toast.failure(error.message);
      } else if (sync === "unknown") {
        // Reloading would replace the teacher's copy with a revision never merged into it.
        toast.failure(SAVE_FAILURE_COPY);
      } else if (conflict) {
        conflictNotice.value = EXAM_WORKSPACE_CONFLICT_COPY;
        toast.failure(EXAM_WORKSPACE_CONFLICT_COPY);
        if (await reloadAfterConflict(currentSummary.lineage_id)) {
          // The reloaded head never held them: arrivals since the save began run again on it.
          arrivals.replayAfterReload();
        }
      } else {
        toast.failure(SAVE_FAILURE_COPY);
      }
      // Every other failure left the teacher's copy, and each arrival's single effect, in place.
      return false;
    } finally {
      arrivals.endHold(openedArrivals);
      keying.endHold(openedKeying);
      operationBusy.value = false;
    }
  }

  /**
   * Spara som: the working copy becomes a new exam named `name` with its own
   * history, and opens in place; the exam it came from keeps its last save.
   */
  async function saveDocumentAs(name: string): Promise<ExamWorkspaceSaveAsOutcome> {
    const current = workspaceDocument.value;
    const currentSummary = summary.value;
    const teacher = state.store.teacher;
    if (!current || !currentSummary || !teacher || state.isBusy.value) {
      return "failed";
    }
    operationBusy.value = true;
    try {
      const response = await teacher.copyExamWorkspaceDocument(currentSummary.lineage_id, name, current);
      state.applyResponse(response);
      keying.invalidateCopy();
      conflictNotice.value = null;
      return "saved";
    } catch (error) {
      if (nameInUse(error)) {
        return "name_taken";
      }
      toast.failure(SAVE_AS_FAILURE_COPY);
      return "failed";
    } finally {
      operationBusy.value = false;
    }
  }

  return { conflictNotice, saveDocument, saveDocumentAs };
}
