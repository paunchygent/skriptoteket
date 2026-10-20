/**
 * Exam workspace unreadable saved exams rows state.
 *
 * Domain purpose:
 *   Own the Öppna drawer's list of saved exams the app cannot read: load
 *   the rows, download a stored file unchanged, and move one to the
 *   papperskorg. A failed load keeps the old rows and shows the saved-list
 *   failure toast; every action disables its own row and never retries.
 *
 * Relationships:
 *   - Transport through `api/examWorkspaceUnreadableFiles.ts`; the vault
 *     download and delete paths are shared with the Mina filer list.
 *   - The list failure copy is the saved list's own (`LIST_FAILURE_COPY`),
 *     exported for this reuse by `useExamWorkspaceSavedList`.
 *   - The success and failure sentences are the shared file notice copy
 *     (`examWorkspaceFileNoticeCopy`); the file itself is written by
 *     `triggerBrowserDownload`.
 *   - Rendered by `ExamWorkspaceUnreadableFiles`; kept free of drawer
 *     assumptions so a later deep link can reuse it.
 */

import { ref } from "vue";
import type { Ref } from "vue";

import type { ExamWorkspaceUnreadableDocument } from "../../../api/examWorkspaceUnreadableFiles";
import {
  downloadSavedExamFile,
  listUnreadableExamWorkspaceDocuments,
  removeSavedExamFile,
} from "../../../api/examWorkspaceUnreadableFiles";
import { useToast } from "../../../composables/useToast";
import { triggerBrowserDownload } from "../../../utils/browserDownload";
import {
  EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_REMOVE_FAILURE_COPY,
  EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVED_COPY,
} from "./examWorkspaceFileNoticeCopy";
import { LIST_FAILURE_COPY } from "./useExamWorkspaceSavedList";

export type UnreadableFilesState = {
  files: Ref<ExamWorkspaceUnreadableDocument[]>;
  /** Lineage ids with a running action; only the acting row is disabled. */
  busyIds: Ref<ReadonlySet<string>>;
  load: () => Promise<void>;
  download: (file: ExamWorkspaceUnreadableDocument) => Promise<void>;
  remove: (file: ExamWorkspaceUnreadableDocument) => Promise<void>;
};

export function useExamWorkspaceUnreadableFiles(): UnreadableFilesState {
  const toast = useToast();
  const files = ref<ExamWorkspaceUnreadableDocument[]>([]);
  const busyIds = ref<ReadonlySet<string>>(new Set());
  /** Bumped by every load, so an older list response cannot overwrite a newer one. */
  let loadRequestId = 0;

  async function load(): Promise<void> {
    loadRequestId += 1;
    const requestId = loadRequestId;
    try {
      const response = await listUnreadableExamWorkspaceDocuments();
      if (requestId !== loadRequestId) {
        return;
      }
      files.value = response.documents;
    } catch {
      if (requestId !== loadRequestId) {
        return;
      }
      toast.failure(LIST_FAILURE_COPY);
    }
  }

  async function download(file: ExamWorkspaceUnreadableDocument): Promise<void> {
    if (busyIds.value.has(file.lineage_id)) return;
    busyIds.value = new Set([...busyIds.value, file.lineage_id]);
    try {
      const response = await downloadSavedExamFile(file.vault_file_id);
      triggerBrowserDownload(response.blob, response.filename ?? file.name);
    } catch {
      toast.failure(EXAM_WORKSPACE_FILE_NOTICE_DOWNLOAD_FAILURE_COPY);
    } finally {
      const next = new Set(busyIds.value);
      next.delete(file.lineage_id);
      busyIds.value = next;
    }
  }

  async function remove(file: ExamWorkspaceUnreadableDocument): Promise<void> {
    if (busyIds.value.has(file.lineage_id)) return;
    busyIds.value = new Set([...busyIds.value, file.lineage_id]);
    try {
      await removeSavedExamFile(file.vault_file_id);
      files.value = files.value.filter((entry) => entry.lineage_id !== file.lineage_id);
      toast.success(EXAM_WORKSPACE_FILE_NOTICE_SAVED_REMOVED_COPY);
      await load();
    } catch {
      toast.failure(EXAM_WORKSPACE_FILE_NOTICE_REMOVE_FAILURE_COPY);
    } finally {
      const next = new Set(busyIds.value);
      next.delete(file.lineage_id);
      busyIds.value = next;
    }
  }

  return { busyIds, download, files, load, remove };
}
