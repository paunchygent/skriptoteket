/**
 * Exam workspace saved-unreadable notice state.
 *
 * Domain purpose:
 *   Own a saved exam the app could not open: the failed route target's
 *   lineage while the shared file notice owns it. Any installed open clears
 *   it; a successful remove clears it too. The view renders the notice from
 *   this state, with download and remove through the shared unreadable files,
 *   so the Öppna drawer's rows reload with the same list.
 *
 * Relationships:
 *   - Composed by `useExamWorkspaceEditing`, which keeps returning the same
 *     fields so consumers do not change; consumed by `ExamWorkspaceView`
 *     through that session.
 *   - Reads the saved list through the document's `savedDocuments` and
 *     `loadSavedDocuments`; download, remove and the unreadable list through
 *     `useExamWorkspaceUnreadableFiles`.
 */

import { computed, ref, type Ref } from "vue";

import type { ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import type { ExamWorkspaceUnreadableDocument } from "../../../api/examWorkspaceUnreadableFiles";
import { useToast } from "../../../composables/useToast";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { OPEN_FAILURE_COPY } from "./useExamWorkspaceDocumentOpen";
import {
  useExamWorkspaceUnreadableFiles,
  type UnreadableFilesState,
} from "./useExamWorkspaceUnreadableFiles";

export type ExamWorkspaceUnreadableTargetDeps = {
  /** The store the unreadable report reads for guest mode. */
  store: ExamWorkspaceStore;
  /** The document's saved list, whose summaries carry the same record fields. */
  savedDocuments: Ref<ExamWorkspaceDocumentSummary[]>;
  /** Reload the document's saved list. */
  loadSavedDocuments: () => Promise<void>;
};

export function useExamWorkspaceUnreadableTarget(deps: ExamWorkspaceUnreadableTargetDeps) {
  const toast = useToast();

  /**
   * A saved exam the app could not open: the failed route target's lineage
   * while the shared file notice owns it. Any installed open clears it; a
   * successful remove clears it too. The view renders the notice from this
   * state, with download and remove through the shared unreadable files
   * below, so the Öppna drawer's rows reload with the same list.
   */
  const unreadableTarget = ref<string | null>(null);
  const unreadableFiles: UnreadableFilesState = useExamWorkspaceUnreadableFiles();
  /** True while the unreadable target's own download or remove runs. */
  const unreadableTargetBusy = computed(
    () => unreadableTarget.value !== null && unreadableFiles.busyIds.value.has(unreadableTarget.value),
  );

  /**
   * Find the failed target's record for download or remove: the unreadable
   * list first, then the saved list (its summaries carry the same fields).
   */
  function resolveUnreadableRecord(lineage: string): ExamWorkspaceUnreadableDocument | null {
    const unreadable = unreadableFiles.files.value.find((entry) => entry.lineage_id === lineage);
    if (unreadable !== undefined) {
      return unreadable;
    }
    const saved = deps.savedDocuments.value.find((entry) => entry.lineage_id === lineage);
    if (saved === undefined) {
      return null;
    }
    return {
      lineage_id: saved.lineage_id,
      name: saved.name,
      saved_at: saved.saved_at,
      title: saved.title,
      vault_file_id: saved.vault_file_id,
    };
  }

  /**
   * The coordinator's unreadable report: show the download-or-remove notice
   * for the target when either list holds it. A guest has no such lists, so
   * it keeps the ordinary open-failure toast, as does a lineage neither
   * list holds. No toast fires on the way to the notice.
   */
  async function noteRouteUnreadable(lineage: string): Promise<void> {
    if (deps.store.teacher === null) {
      toast.failure(OPEN_FAILURE_COPY);
      return;
    }
    await unreadableFiles.load();
    if (unreadableFiles.files.value.some((entry) => entry.lineage_id === lineage)) {
      unreadableTarget.value = lineage;
      return;
    }
    await deps.loadSavedDocuments();
    if (deps.savedDocuments.value.some((entry) => entry.lineage_id === lineage)) {
      unreadableTarget.value = lineage;
      return;
    }
    toast.failure(OPEN_FAILURE_COPY);
  }

  /** An installed open clears the unreadable notice, whatever it reported before. */
  function clearOnInstalled(): void {
    unreadableTarget.value = null;
  }

  /** Download the notice's stored file unchanged through the shared path. */
  async function downloadUnreadableTarget(): Promise<void> {
    const lineage = unreadableTarget.value;
    if (lineage === null) {
      return;
    }
    const record = resolveUnreadableRecord(lineage);
    if (record === null) {
      return;
    }
    await unreadableFiles.download(record);
  }

  /**
   * Move the notice's stored file to the papperskorg through the shared
   * path. A successful remove clears the target and reloads the lists the
   * Öppna drawer reads; the record staying in either list keeps the notice.
   */
  async function removeUnreadableTarget(): Promise<void> {
    const lineage = unreadableTarget.value;
    if (lineage === null) {
      return;
    }
    const record = resolveUnreadableRecord(lineage);
    if (record === null) {
      return;
    }
    await unreadableFiles.remove(record);
    await deps.loadSavedDocuments();
    const removed =
      !unreadableFiles.files.value.some((entry) => entry.lineage_id === lineage) &&
      !deps.savedDocuments.value.some((entry) => entry.lineage_id === lineage);
    if (removed) {
      unreadableTarget.value = null;
    }
  }

  return {
    unreadableTarget,
    unreadableTargetBusy,
    unreadableFiles,
    noteRouteUnreadable,
    clearOnInstalled,
    downloadUnreadableTarget,
    removeUnreadableTarget,
  };
}
