/**
 * Exam workspace new-exam flow (TASK-SKRIPT-40-04-21).
 *
 * Domain purpose:
 *   One click on "Nytt prov" opens a new untitled exam with one empty
 *   question, ready to edit. The open exam, if any, is saved first, exactly
 *   as Öppna refuses to switch until it is: the same open gate blocks this
 *   flow and toasts its reason. A guest whose open browser draft has content
 *   confirms first; everyone else creates at once. A teacher's new exam is
 *   saved at once and appears in the Prov list.
 *
 * Relationships:
 *   - Created once by `ExamWorkspaceView`, which passes the editing session,
 *     the store, the routed open and its toast, and renders the confirm
 *     dialog beside the Spara som dialog.
 *   - Creates through `examWorkspaceNewExam`; the gate is the one
 *     `useExamWorkspaceOpenBlocking` owns, never a second gate.
 */

import { ref } from "vue";
import type { Ref } from "vue";

import {
  createNewExam,
  examWorkspaceDraftHasContent,
  NEW_EXAM_FAILURE_COPY,
} from "./examWorkspaceNewExam";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { serverImportMessage } from "./useExamWorkspaceConversion";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import { useExamWorkspaceOpenBlocking } from "./useExamWorkspaceOpenBlocking";

export type UseExamWorkspaceNewExamDeps = {
  /** The editing session: its open gate, its draft and its saved list. */
  editing: Pick<
    ReturnType<typeof useExamWorkspaceEditing>,
    "history" | "isBusy" | "isDirty" | "isOpenBlockedByOtherOperation" | "loadSavedDocuments" | "workspaceDocument"
  >;
  /** The exam workspace store; the teacher half wins, the guest half follows. */
  store: ExamWorkspaceStore;
  /** Open the created exam by its lineage id, as the Öppna list's open command does. */
  openRoutedDocument: (lineageId: string) => void;
  /** Failures toast; the open gate's own reason toasts through this too. */
  toast: { failure: (message: string) => void };
};

export function useExamWorkspaceNewExam(deps: UseExamWorkspaceNewExamDeps): {
  busy: Ref<boolean>;
  confirmOpen: Ref<boolean>;
  start: () => Promise<void>;
  confirmReplace: () => Promise<void>;
  cancelReplace: () => void;
} {
  const busy = ref(false);
  const confirmOpen = ref(false);
  const { editing, store, openRoutedDocument, toast } = deps;

  const { openBlocked, blockedReason } = useExamWorkspaceOpenBlocking({
    isBusy: () => editing.isBusy.value,
    isDirty: () => editing.isDirty.value,
    saveState: () => editing.history.saveStatus.value.state,
    saveDetail: () => {
      const status = editing.history.saveStatus.value;
      return status.state === "unsaved" ? status.detail : null;
    },
    isOpenBlockedByOtherOperation: () => editing.isOpenBlockedByOtherOperation.value,
  });

  async function create(): Promise<void> {
    busy.value = true;
    try {
      const lineageId = await createNewExam(store);
      if (lineageId === null) {
        throw new Error("No exam workspace store side can create a new exam.");
      }
      if (store.teacher !== null) {
        await editing.loadSavedDocuments();
      }
      openRoutedDocument(lineageId);
    } catch (error) {
      toast.failure(serverImportMessage(error) ?? NEW_EXAM_FAILURE_COPY);
    } finally {
      busy.value = false;
    }
  }

  async function start(): Promise<void> {
    if (busy.value) return;
    if (openBlocked.value) {
      if (blockedReason.value !== null) {
        toast.failure(blockedReason.value);
      }
      return;
    }
    if (store.teacher === null) {
      const draft = editing.workspaceDocument.value;
      if (draft !== null && examWorkspaceDraftHasContent(draft)) {
        confirmOpen.value = true;
        return;
      }
    }
    await create();
  }

  async function confirmReplace(): Promise<void> {
    confirmOpen.value = false;
    await create();
  }

  function cancelReplace(): void {
    confirmOpen.value = false;
  }

  return { busy, confirmOpen, start, confirmReplace, cancelReplace };
}
