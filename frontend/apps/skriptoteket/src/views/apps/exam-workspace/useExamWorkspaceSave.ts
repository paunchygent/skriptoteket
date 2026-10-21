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
 *   The copy POST is a replacement candidate, never a direct install: this
 *   module starts the transport and holds the copy busy while it runs, and
 *   the gate-owned replacement coordinator admits the result only while its
 *   intent is still desired and its token is current. A retired copy installs
 *   nothing, projects nothing and is never deleted as cleanup.
 *
 * Relationships:
 *   - Transport through the exam workspace store.
 *   - The coordinator adopts a current copy response through the same opening
 *     transition as a route target, once.
 *   - Marks the copy busy flag while a request runs; the coordinator releases
 *     it synchronously when it retires the copy selection, so a newer target
 *     is never refused behind the retired copy.
 */

import type { ComputedRef, Ref } from "vue";

import { isApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import type { ExamWorkspaceStore, GuestSlotAdmission } from "./examWorkspaceStore";
import type { FenceToken, SyncFence } from "./examWorkspaceSyncFence";

export const RELOAD_FAILURE_COPY = "Det gick inte att läsa in provet på nytt. Försök igen.";
export const SAVE_AS_FAILURE_COPY = "Det gick inte att spara en kopia av provet. Försök igen.";

export type ExamWorkspaceSaveAsOutcome = "saved" | "name_taken" | "failed";

type SaveState = {
  workspaceDocument: Ref<NativeExamDocument | null>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  /** The server's newest undo step; a source exam is open exactly when the summary names one. */
  historyCursor: Ref<string | null>;
  isBusy: ComputedRef<boolean>;
  /** The copy's own busy hold; set while its POST runs, cleared by its own settle or its retire. */
  copyBusy: Ref<boolean>;
  /** The generation owner; the hold belongs to the token minted at dispatch. */
  getFence: () => SyncFence;
  /** The store the save reads and writes run through. */
  store: ExamWorkspaceStore;
};

/** True when the copy failure means the requested name is taken (silent, no toast). */
export function isCopyNameTaken(error: unknown): boolean {
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
  const { copyBusy, summary, workspaceDocument } = state;

  /**
   * Spara som: start copying the working exam under `name` with its own
   * history. The caller stored any pending edit first; the sent copy is read
   * here, synchronously at dispatch. The returned POST promise is a candidate
   * the owning coordinator settles through the fence. Null when the copy
   * guards refuse (no exam, no teacher, or another operation holds the
   * document). The hold belongs to this copy's own fence token, so a retired
   * copy's late settle never clears a newer copy's hold.
   */
  function beginCopy(
    sourceLineageId: string,
    name: string,
  ): Promise<ExamWorkspaceDocumentResponse> | null {
    const sent = workspaceDocument.value;
    const currentSummary = summary.value;
    const teacher = state.store.teacher;
    if (!sent || !currentSummary || !teacher || state.isBusy.value) {
      return null;
    }
    const fence = state.getFence();
    const token: FenceToken = fence.begin();
    copyBusy.value = true;
    const posting = teacher.copyExamWorkspaceDocument(sourceLineageId, name, sent);
    const owned = posting.then(
      (response) => {
        if (fence.isCurrent(token)) {
          copyBusy.value = false;
        }
        return response;
      },
      (error: unknown) => {
        if (fence.isCurrent(token)) {
          copyBusy.value = false;
        }
        throw error;
      },
    );
    return owned;
  }

  /**
   * Nytt prov: create the blank exam and read it back as a document
   * response, a candidate the owning coordinator settles through the fence.
   * Null when the guards refuse: another operation holds the document, no
   * side can create, or a source exam is open and its current history cursor
   * is no longer `expectedCursor` (the draft the D9 check read changed
   * meanwhile). The hold belongs to this creation's own fence token, so a
   * retired creation's late settle never clears a newer creation's hold.
   * A guest creation writes the browser slot under `admission`: the write
   * happens only while the creation still holds live replacement authority
   * and no other tab holds a live edit lease.
   */
  function beginNewExam(
    expectedCursor: string | null,
    admission: GuestSlotAdmission,
  ): Promise<ExamWorkspaceDocumentResponse> | null {
    const teacher = state.store.teacher;
    const guest = state.store.guest;
    if ((!teacher && !guest) || state.isBusy.value) {
      return null;
    }
    if (state.summary.value !== null && state.historyCursor.value !== expectedCursor) {
      return null;
    }
    const fence = state.getFence();
    const token: FenceToken = fence.begin();
    copyBusy.value = true;
    const posting = (async (): Promise<ExamWorkspaceDocumentResponse> => {
      if (teacher) {
        const created = await teacher.createExamWorkspaceBlank();
        return await state.store.shared.getExamWorkspaceDocument(created.lineage_id);
      }
      if (guest) {
        const lineageId = await guest.startBlank(expectedCursor, admission);
        return await state.store.shared.getExamWorkspaceDocument(lineageId);
      }
      throw new Error("No exam workspace store side can create a new exam.");
    })();
    const owned = posting.then(
      (response) => {
        if (fence.isCurrent(token)) {
          copyBusy.value = false;
        }
        return response;
      },
      (error: unknown) => {
        if (fence.isCurrent(token)) {
          copyBusy.value = false;
        }
        throw error;
      },
    );
    return owned;
  }

  return { beginCopy, beginNewExam, copyBusy };
}
