/**
 * Exam workspace saving.
 *
 * Domain purpose:
 *   Store the working copy as a new exam with Spara som. Every other write
 *   is an autosaved history step (TASK-SKRIPT-40-04-14, one save model), so
 *   there is no Spara path here: `useExamWorkspaceEditing.save` stores a
 *   pending edit as a step through the history, and Spara som stores first
 *   through that same flush before it copies the working exam.
 *
 * Relationships:
 *   - Transport through the exam workspace store.
 *   - Installs the copy response through the document's `applyResponse`;
 *     reads go through its `beginDocumentRead` so renames stay reconciled.
 *   - AI suggestion and gap keying replays run through `arrivals` and
 *     `keying`: the response holds the payload, so arrivals that landed after
 *     the copy request run again on it.
 *   - Marks the shared operation busy flag while a request runs.
 */

import type { ComputedRef, Ref } from "vue";

import { isApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import type { FenceToken } from "./examWorkspaceSyncFence";
import type { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";
import type { useExamWorkspaceGapKeying } from "./useExamWorkspaceGapKeying";
import type { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";

export const RELOAD_FAILURE_COPY = "Det gick inte att läsa in provet på nytt. Försök igen.";
const SAVE_AS_FAILURE_COPY = "Det gick inte att spara en kopia av provet. Försök igen.";

export type ExamWorkspaceSaveAsOutcome = "saved" | "name_taken" | "failed";

type SaveState = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  isBusy: ComputedRef<boolean>;
  operationBusy: Ref<boolean>;
  applyResponse: (token: FenceToken, response: ExamWorkspaceDocumentResponse) => void;
  beginDocumentRead: () => (response: ExamWorkspaceDocumentResponse) => ExamWorkspaceDocumentResponse;
  isCurrent: (token: FenceToken) => boolean;
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

export function useExamWorkspaceSave(state: SaveState) {
  const toast = useToast();
  const { keying, operationBusy, summary, workspaceDocument } = state;

  /**
   * Spara som: the working copy becomes a new exam named `name` with its own
   * history, and opens in place; the exam it came from keeps its last save.
   * The caller stores any pending edit first and hands over the token its
   * operation started with, so the copy and its install belong to that
   * operation. A retired answer installs nothing.
   */
  async function saveDocumentAs(name: string, token: FenceToken): Promise<ExamWorkspaceSaveAsOutcome> {
    const current = workspaceDocument.value;
    const currentSummary = summary.value;
    const teacher = state.store.teacher;
    if (!current || !currentSummary || !teacher || state.isBusy.value || !state.isCurrent(token)) {
      return "failed";
    }
    operationBusy.value = true;
    try {
      const response = await teacher.copyExamWorkspaceDocument(currentSummary.lineage_id, name, current);
      if (!state.isCurrent(token)) {
        return "failed";
      }
      state.applyResponse(token, response);
      keying.invalidateCopy();
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

  return { saveDocumentAs };
}
