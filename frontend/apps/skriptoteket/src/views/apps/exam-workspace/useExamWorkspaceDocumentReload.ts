/**
 * Exam workspace document reload.
 *
 * Domain purpose:
 *   Read the exam again after a conflict: wait out an in-flight operation,
 *   drop when another exam replaced the captured one, install the fresh
 *   response while current, and show a failure toast when the read fails.
 *
 * Relationships:
 *   - Used by `useExamWorkspaceDocument`, which hands over its summary, its
 *     fence resolver, its busy flags, its rename-reconciled read, its store
 *     read, its install call, and the keying and arrival-replay callbacks.
 *   - Transport through the exam workspace store's shared document read.
 *   - Installs through the document's `applyResponse`; keying invalidation
 *     and arrival replay run through their callbacks.
 *   - Shows the failure through `useToast`, which specs mock by module path.
 */

import { watch } from "vue";
import type { ComputedRef, Ref } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import type { FenceToken, SyncFence } from "./examWorkspaceSyncFence";
import { RELOAD_FAILURE_COPY } from "./useExamWorkspaceSave";

export type ExamWorkspaceDocumentReloadDeps = {
  /** The open exam's summary; a missing summary means there is nothing to reload. */
  summary: Ref<ExamWorkspaceDocumentSummary | null>;
  /** The sync gate's generation owner; every reload carries its token. */
  resolveFence: () => SyncFence;
  /** True while an operation other than an open read holds the document. */
  isOperationBusy: ComputedRef<boolean>;
  /** The reload sets this while its own read runs. */
  operationBusy: Ref<boolean>;
  /** Capture rename ordering before the GET; reconciled in the read continuation. */
  beginDocumentRead: () => (response: ExamWorkspaceDocumentResponse) => ExamWorkspaceDocumentResponse;
  /** The store the document read runs through; only `shared.getExamWorkspaceDocument` is used. */
  store: ExamWorkspaceStore;
  /** Install the fresh response; runs only while the token is current. */
  applyResponse: (token: FenceToken, response: ExamWorkspaceDocumentResponse) => void;
  /** Drop in-flight keying replies for the copy the install replaced. */
  invalidateCopy: () => void;
  /** Run held suggestion arrivals again on the installed document. */
  replayArrivalsAfterReload: () => void;
};

export function useExamWorkspaceDocumentReload(deps: ExamWorkspaceDocumentReloadDeps) {
  const toast = useToast();

  /**
   * Read the exam again, also the conflict recovery of undo and the server
   * commands. A 409 during an operation waits for it to end; a retired
   * answer installs nothing. The initiating context must still own the
   * install: when another exam replaced the captured one while this reload
   * waited or read, the reload drops instead of seizing the newer target.
   */
  async function reloadDocument(): Promise<void> {
    const currentSummary = deps.summary.value;
    if (!currentSummary) return;
    const lineageId = currentSummary.lineage_id;
    const fence = deps.resolveFence();
    const token = fence.begin();
    if (deps.isOperationBusy.value) {
      // A busy-time 409 waits for the operation instead of skipping the
      // reload; the watch resolves when the operation clears without a timer.
      await new Promise<void>((resolve) => {
        const stop = watch(deps.isOperationBusy, (busy) => {
          if (!busy) { stop(); resolve(); }
        }, { immediate: true });
      });
    }
    if (!fence.isCurrent(token)) {
      // The wait outlived the generation: no independent handoff may seize a
      // newer target, so the retired reload drops without installing anything.
      return;
    }
    if (deps.summary.value?.lineage_id !== lineageId) {
      return;
    }
    deps.operationBusy.value = true;
    try {
      const reconcile = deps.beginDocumentRead();
      const response = reconcile(
        await deps.store.shared.getExamWorkspaceDocument(lineageId),
      );
      if (!fence.isCurrent(token)) {
        return;
      }
      if (deps.summary.value?.lineage_id !== lineageId) {
        return;
      }
      deps.applyResponse(token, response);
      deps.invalidateCopy();
      deps.replayArrivalsAfterReload();
    } catch {
      toast.failure(RELOAD_FAILURE_COPY);
    } finally {
      deps.operationBusy.value = false;
    }
  }

  return { reloadDocument };
}
