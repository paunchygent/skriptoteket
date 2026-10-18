/**
 * Exam workspace one-question reconversion request lifecycle.
 *
 * Domain purpose:
 *   Reconvert one review question from the saved revision's stored source
 *   with the teacher's chosen type (TASK-SKRIPT-39-05-09 D1). The reply
 *   replaces only that draft item, and only while the same opening still
 *   stands on the same revision with that item unedited; a reply that lost
 *   its place, or a failure of a request that did, changes nothing. One
 *   retry runs at a time: it holds the document owner's request lock for
 *   its whole request, so open, save and import are serialized behind it.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceDocument`, which hands over its document
 *     refs, its request lock and its combined busy state.
 *   - Reads and replaces only the retry target through the document owner's
 *     `workspaceDocument` ref.
 *   - Delegates transport to the exam workspace store's teacher services.
 *   - Compares the target with `sameValue` from `examWorkspaceConversionMerge`.
 */

import type { Ref, ShallowRef } from "vue";

import { isApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
  NativeExamItemKind,
} from "../../../api/examWorkspace";
import { useAiAccess } from "../../../composables/useAiAccess";
import { useToast } from "../../../composables/useToast";
import { sameValue } from "./examWorkspaceConversionMerge";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";
import type { ExamWorkspaceOpening } from "./useExamWorkspaceDocument";

const RETRY_FAILURE_COPY = "Det gick inte att konvertera om frågan. Försök igen.";

/** The document owner's state a retry reads and updates around its request. */
export type ExamWorkspaceItemRetryBinding = {
  /** The draft copy; only the retried item is replaced in it. */
  workspaceDocument: Ref<NativeExamDocument | null>;
  /** The saved revision the draft stands on; a newer server copy drops the reply. */
  serverDocument: Ref<NativeExamDocument | null>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  /** The opening the request was sent for; a newer opening drops its reply. */
  openExam: Readonly<ShallowRef<ExamWorkspaceOpening | null>>;
  /** The one request lock shared with open, save and import. */
  operationBusy: Ref<boolean>;
  /** The document owner's combined busy state; a retry sends nothing while it holds. */
  isBusy: () => boolean;
  /** The teacher services the retry runs through; null in guest mode. */
  teacher: ExamWorkspaceTeacherServices | null;
};

export function useExamWorkspaceItemRetry(binding: ExamWorkspaceItemRetryBinding) {
  const toast = useToast();
  // The paid reconversion is admin-only until the spend cap ships (TASK-SKRIPT-REP-0044 L3).
  const { canUseAi } = useAiAccess();

  /**
   * The opening, lineage and saved revision a retry request was sent for are
   * still the ones in front of the teacher.
   */
  function retryRequestIsLive(
    opening: ExamWorkspaceOpening,
    lineageId: string,
    revision: number,
  ): boolean {
    return (
      binding.openExam.value === opening &&
      binding.summary.value?.lineage_id === lineageId &&
      binding.workspaceDocument.value?.revision === revision &&
      binding.serverDocument.value?.revision === revision
    );
  }

  /** Send the retry for one question that still holds its stored source and awaits review. */
  async function retryItem(itemId: string, kind: NativeExamItemKind): Promise<void> {
    const current = binding.workspaceDocument.value;
    const currentSummary = binding.summary.value;
    const opening = binding.openExam.value;
    const teacher = binding.teacher;
    if (!canUseAi.value || !current || !currentSummary || !opening || !teacher || binding.isBusy()) {
      return;
    }
    const target = current.items.find((item) => item.item_id === itemId) ?? null;
    if (
      target === null ||
      target.retry_source === null ||
      target.review.state !== "review_required"
    ) {
      return;
    }
    const lineageId = currentSummary.lineage_id;
    const revision = current.revision;
    binding.operationBusy.value = true;
    try {
      const response = await teacher.retryExamWorkspaceItem(lineageId, current, itemId, kind);
      const draft = binding.workspaceDocument.value;
      const draftTarget = draft?.items.find((item) => item.item_id === itemId) ?? null;
      if (
        draft === null ||
        response.lineage_id !== lineageId ||
        !retryRequestIsLive(opening, lineageId, revision) ||
        draftTarget === null ||
        !sameValue(draftTarget, target)
      ) {
        return;
      }
      binding.workspaceDocument.value = {
        ...draft,
        items: draft.items.map((item) => (item.item_id === itemId ? response.item : item)),
      };
    } catch (error) {
      if (!retryRequestIsLive(opening, lineageId, revision)) {
        return;
      }
      const serverCopy =
        isApiError(error) && error.code !== "HTTP_ERROR" && error.message !== "Validation error"
          ? error.message
          : null;
      toast.failure(serverCopy || RETRY_FAILURE_COPY);
    } finally {
      binding.operationBusy.value = false;
    }
  }

  return { retryItem };
}
