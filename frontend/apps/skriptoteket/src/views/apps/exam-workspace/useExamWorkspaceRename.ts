/** Own immediate vault rename outcomes for the open exam, beyond the drawer lifetime. */
import { computed, shallowRef, type Ref } from "vue";

import { isApiError } from "../../../api/client";
import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import { renameVaultFile } from "../../../api/vault";
import { useToast } from "../../../composables/useToast";

export type ExamWorkspaceRenameFailure = { stem: string; message: string };

type RenameState = {
  isBusy: () => boolean;
  operationBusy: Ref<boolean>;
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  savedDocuments: Ref<ExamWorkspaceDocumentSummary[]>;
};

export function useExamWorkspaceRename(state: RenameState) {
  const toast = useToast();
  let completionSequence = 0;
  const completedNames = new Map<string, { name: string; sequence: number }>();

  /** Preserve completed renames only against snapshots requested before their completion. */
  function beginSummaryRead() {
    const requestedAt = completionSequence;
    return (summary: ExamWorkspaceDocumentSummary): ExamWorkspaceDocumentSummary => {
      const completed = completedNames.get(summary.lineage_id);
      if (!completed) return summary;
      if (requestedAt < completed.sequence) return { ...summary, name: completed.name };
      // A later request is authoritative, including a rename made elsewhere.
      completed.name = summary.name;
      return summary;
    };
  }

  const failure = shallowRef<(ExamWorkspaceRenameFailure & { lineageId: string }) | null>(null);
  const renameFailure = computed(() =>
    failure.value?.lineageId === state.summary.value?.lineage_id ? failure.value : null,
  );

  /** Null means the owner reported failure; the drawer keeps the attempted stem for retry. */
  async function renameFile(fileId: string, stem: string): Promise<string | null> {
    if (state.isBusy()) return null;
    // A conversion read already in flight may replace this head while rename awaits its reply.
    const lineageId = state.summary.value?.vault_file_id === fileId
      ? state.summary.value.lineage_id
      : state.savedDocuments.value.find((entry) => entry.vault_file_id === fileId)?.lineage_id;
    if (!lineageId) return null;
    state.operationBusy.value = true;
    failure.value = null;
    try {
      const result = await renameVaultFile(fileId, stem);
      const name = result.file.name;
      completedNames.set(lineageId, { name, sequence: ++completionSequence });
      state.savedDocuments.value = state.savedDocuments.value.map((entry) =>
        entry.lineage_id === lineageId ? { ...entry, name } : entry,
      );
      if (state.summary.value?.lineage_id === lineageId) {
        state.summary.value = { ...state.summary.value, name };
      }
      return name;
    } catch (error) {
      const message = isApiError(error)
        ? (typeof error.details === "string" ? error.details : error.message)
        : "Det gick inte att byta filnamn. Försök igen.";
      failure.value = { lineageId, stem, message };
      toast.failure(message);
      return null;
    } finally {
      state.operationBusy.value = false;
    }
  }

  return { beginSummaryRead, renameFailure, renameFile };
}
