/**
 * Exam workspace saved-exams list.
 *
 * Domain purpose:
 *   Own the teacher's list of saved exams: load it, merge it with what is
 *   already shown, keep the open exam's entry current after every response,
 *   and report its ordering.
 *
 * Relationships:
 *   - Transport through the shared store half (`listExamWorkspaceDocuments`).
 *   - Reads reconcile summaries against completed renames through the
 *     provider `useExamWorkspaceDocument` passes in (`useExamWorkspaceRename`).
 *   - `useExamWorkspaceDocument` records each installed summary here;
 *     `useExamWorkspaceRename` updates the exposed list on a rename.
 */

import { ref } from "vue";

import type { ExamListOrdering, ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { mergeSavedDocuments } from "./examWorkspaceSavedDocuments";
import type { ExamWorkspaceTeacherServices } from "./examWorkspaceStore";

const LIST_FAILURE_COPY = "Det gick inte att hämta dina sparade prov.";

type SummaryReconcile = (summary: ExamWorkspaceDocumentSummary) => ExamWorkspaceDocumentSummary;

type SavedListState = {
  /** Captures rename ordering before a read; the result reconciles that read's summaries. */
  beginSummaryRead: () => SummaryReconcile;
  /** The teacher services the saved list loads through; null in guest mode. */
  teacher: ExamWorkspaceTeacherServices | null;
};

export function useExamWorkspaceSavedList(state: SavedListState) {
  const toast = useToast();
  const savedDocuments = ref<ExamWorkspaceDocumentSummary[]>([]);
  const listOrdering = ref<ExamListOrdering>("course");

  /** Replace the exam's entry with `summary`, or put it first when it is not listed yet. */
  function recordSummary(summary: ExamWorkspaceDocumentSummary): void {
    savedDocuments.value = savedDocuments.value.some((entry) => entry.lineage_id === summary.lineage_id)
      ? savedDocuments.value.map((entry) => (entry.lineage_id === summary.lineage_id ? summary : entry))
      : [summary, ...savedDocuments.value];
  }

  async function loadSavedDocuments(): Promise<void> {
    const teacher = state.teacher;
    if (!teacher) return;
    const reconcile = state.beginSummaryRead();
    try {
      const response = await teacher.listExamWorkspaceDocuments();
      savedDocuments.value = mergeSavedDocuments(savedDocuments.value, response.documents.map(reconcile));
      listOrdering.value = response.ordering;
    } catch {
      toast.failure(LIST_FAILURE_COPY);
    }
  }

  return { listOrdering, loadSavedDocuments, recordSummary, savedDocuments };
}
