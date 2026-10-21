/**
 * Exam workspace new-exam flow (TASK-SKRIPT-40-04-21).
 *
 * Domain purpose:
 *   One click on "Nytt prov" opens a new untitled exam with one empty
 *   question, ready to edit. Nytt prov is a third intent of the existing
 *   replacement coordinator, modelled on Spara som: the open exam, if any,
 *   settles behind the shared barrier first, and the coordinator alone
 *   installs the blank response and projects the new address. The open gate
 *   blocks this flow and toasts its reason, exactly as Öppna refuses to
 *   switch until the exam is saved. A guest whose open browser draft has
 *   content confirms first; everyone else creates at once. A teacher's new
 *   exam is saved at once and appears in the Prov list.
 *
 * Relationships:
 *   - Created once by `ExamWorkspaceView`, which passes the editing session,
 *     the store and its toast, and renders the confirm dialog beside the
 *     Spara som dialog.
 *   - Creates through the editing session's `newExam`, which registers the
 *     intent with the gate-owned replacement coordinator before its first
 *     await; the gate is the one `useExamWorkspaceOpenBlocking` owns, never
 *     a second gate. The coordinator owns the failure toast, so this flow
 *     never toasts twice.
 */

import { ref } from "vue";
import type { Ref } from "vue";

import { examWorkspaceDraftHasContent } from "./examWorkspaceNewExam";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExamWorkspaceNewExamOutcome } from "./examWorkspaceReplacementTypes";
import { useExamWorkspaceOpenBlocking } from "./useExamWorkspaceOpenBlocking";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";

type Editing = ReturnType<typeof useExamWorkspaceEditing>;

export type UseExamWorkspaceNewExamDeps = {
  /**
   * The editing session: its open gate, the draft the D9 check reads with
   * its history cursor, the coordinator-backed `newExam`, and the saved list
   * a teacher's creation reloads.
   */
  editing: Pick<
    Editing,
    | "historyCursor"
    | "isBusy"
    | "isDirty"
    | "isOpenBlockedByOtherOperation"
    | "loadSavedDocuments"
    | "newExam"
    | "workspaceDocument"
  > & {
    history: Pick<Editing["history"], "saveStatus">;
  };
  /** The exam workspace store; the teacher half wins, the guest half follows. */
  store: ExamWorkspaceStore;
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
  /** The D9 check's cursor while the guest confirm is open. */
  const checkedCursor: Ref<string | null> = ref(null);
  const { editing, store, toast } = deps;

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

  /** Toast the gate's reason while it blocks; true means the caller stops. */
  function toastBlocked(): boolean {
    if (!openBlocked.value) {
      return false;
    }
    if (blockedReason.value !== null) {
      toast.failure(blockedReason.value);
    }
    return true;
  }

  async function submit(cursor: string | null): Promise<void> {
    busy.value = true;
    try {
      const outcome: ExamWorkspaceNewExamOutcome = await editing.newExam(cursor);
      if (outcome === "created" && store.teacher !== null) {
        await editing.loadSavedDocuments();
      }
    } finally {
      busy.value = false;
    }
  }

  async function start(): Promise<void> {
    if (busy.value) return;
    if (toastBlocked()) {
      return;
    }
    const cursor = editing.historyCursor.value;
    if (store.teacher === null) {
      const draft = editing.workspaceDocument.value;
      if (draft !== null && examWorkspaceDraftHasContent(draft)) {
        checkedCursor.value = cursor;
        confirmOpen.value = true;
        return;
      }
    }
    await submit(cursor);
  }

  async function confirmReplace(): Promise<void> {
    confirmOpen.value = false;
    if (toastBlocked()) {
      return;
    }
    if (editing.historyCursor.value !== checkedCursor.value) {
      await start();
      return;
    }
    await submit(checkedCursor.value);
  }

  function cancelReplace(): void {
    confirmOpen.value = false;
  }

  return { busy, confirmOpen, start, confirmReplace, cancelReplace };
}
