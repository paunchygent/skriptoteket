/**
 * Exam workspace editing session.
 *
 * Domain purpose:
 *   Join the open exam, its server-stored undo history and the structure
 *   commands into one editing session: every teacher edit becomes an undo
 *   step through a 900 ms pause or at once, and the step store also writes
 *   the exam file (TASK-SKRIPT-40-04-14, one save model). The sync gate owns
 *   the phase, the kept refused edit and the single write queue: every lock
 *   reads `gate.editingLocked`, every write runs through
 *   `gate.enqueueWrite`, and every cursor the gate did not install is
 *   reported back to it. An `EDIT_LEASE_HELD` refusal or a lost lease reaches
 *   the gate as `leaseLost`, a stale-cursor 409 as `staleConflict`, and a
 *   held lease as `leaseAcquired`. It owns `selectedParentId` (the part
 *   entry the teacher selected) so structural inserts land after the
 *   selected part; the selection composable drives it.
 *
 * Relationships:
 *   - Composes `useExamWorkspaceDocument`, `useExamWorkspaceHistory`,
 *     `useExamWorkspaceStructure` and `useExamWorkspaceSyncGate`; consumed
 *     by `ExamWorkspaceView`.
 */

import { computed, onScopeDispose, ref, watch } from "vue";

import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { useToast } from "../../../composables/useToast";
import { mergeRefusedEdit } from "./examWorkspaceRefusedEditMerge";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import {
  useExamWorkspaceEditLease,
  type ExamWorkspaceEditLeaseDeps,
} from "./useExamWorkspaceEditLease";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";
import { createSyncGateTimer, useExamWorkspaceSyncGate } from "./useExamWorkspaceSyncGate";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";
import { LEASE_LOST_COPY, type ExamWorkspaceSaveStatus } from "./useExamWorkspaceSaveStatus";
import { RELOAD_FAILURE_COPY } from "./useExamWorkspaceSave";

/** The lease seams specs override; production uses the transport and the browser slot. */
export type ExamWorkspaceEditingLeaseOverrides = Partial<
  Pick<
    ExamWorkspaceEditLeaseDeps,
    "guestStorage" | "now" | "openGuestChannel" | "server" | "tabId"
  >
>;

export function useExamWorkspaceEditing(store: ExamWorkspaceStore, lease?: ExamWorkspaceEditingLeaseOverrides) {
  const toast = useToast();
  let noteEdit: (structural: boolean, before: NativeExamDocument | null) => void = () => undefined;
  // The selection composable is built by the view after this session; it registers
  // its part-entry selection here so a new part's instruction opens in the editor.
  let selectParent: (parentId: string) => void = () => undefined;
  // The part entry the teacher selected, shared with the selection composable
  // and the structure commands so Ny del and Ny instruktion land after it.
  const selectedParentId = ref<string | null>(null);
  // The lease session, assigned after the document, history and structure it
  // drives exist. The holder object stays stable so every closure above tracks
  // the document's reactive state directly; each closure only runs once the
  // session is in place.
  const leaseHolder: { session: ReturnType<typeof useExamWorkspaceEditLease> | null } = {
    session: null,
  };
  // A cursor the gate's own install set: the history watcher must not report
  // it back as foreign. Consumed on the first matching cursor event.
  let gateCursor: { lineage: string; cursor: string } | null = null;
  const document = useExamWorkspaceDocument({
    isReadOnly: () => gate.editingLocked.value,
    onEdit: (structural, before) => noteEdit(structural, before),
    store,
  });
  const lineageId = () => document.summary.value?.lineage_id ?? null;

  const history = useExamWorkspaceHistory({
    historyCursor: document.historyCursor,
    install: document.installDocument,
    isReadOnly: () => gate.editingLocked.value,
    isReplacing: () => document.isReplacing.value,
    // Not `isBusy`: that includes the replacing lock the history's own reads hold.
    isBlocked: () => document.isOperationBusy.value,
    lineageId,
    noteExportBlockers: document.noteExportBlockers,
    noteInstalledCursor: (foreignLineageId, cursor) => {
      if (
        gateCursor !== null &&
        gateCursor.lineage === foreignLineageId &&
        gateCursor.cursor === cursor
      ) {
        gateCursor = null;
        return true;
      }
      gate.foreignCursor(true);
      return false;
    },
    noteGateStored: () => gate.noteStored(),
    noteLeaseLost: () => leaseHolder.session?.noteLostLease(),
    noteStored: document.noteStored,
    isGuest: () => store.guest !== null,
    onConflict: () => {
      gate.staleConflict();
      return Promise.resolve();
    },
    replaceCopy: document.replaceCopy,
    savedRevision: () => document.savedRevision.value,
    enqueueWrite: (run, refused) => gate.enqueueWrite(run, refused),
    shared: store.shared,
    tabId: () => leaseHolder.session?.tabId ?? "",
    workspaceDocument: document.workspaceDocument,
  });
  noteEdit = history.noteEdit;

  const structure = useExamWorkspaceStructure({
    applyCommandResponse: (response) => applyCommandResponse(response),
    editDocument: document.editDocument,
    flush: history.flush,
    historyCursor: document.historyCursor,
    isBusy: () => document.isBusy.value || history.storing.value,
    isReadOnly: () => gate.editingLocked.value,
    lineageId,
    noteLeaseLost: () => leaseHolder.session?.noteLostLease(),
    onConflict: () => {
      gate.staleConflict();
      return Promise.resolve();
    },
    replaceCopy: document.replaceCopy,
    savedRevision: () => document.savedRevision.value,
    selectItem: document.selectItem,
    selectParent: (parentId) => selectParent(parentId),
    selectedItemId: document.selectedItemId,
    selectedParentId,
    shared: store.shared,
    tabId: () => leaseHolder.session?.tabId ?? "",
    workspaceDocument: document.workspaceDocument,
  });

  const gate = useExamWorkspaceSyncGate({
    isLeaseHeld: () => leaseHolder.session !== null && !leaseHolder.session.readOnly.value,
    hasPendingEdit: () => history.pending.value,
    currentStepDocument: () => history.stepDocument.value,
    currentWorkingCopy: () => document.workspaceDocument.value,
    dropOwedSnapshots: () => history.dropOwedSnapshots(),
    readDocument: (readLineageId) => store.shared.getExamWorkspaceDocument(readLineageId),
    readSteps: (readLineageId, base) => history.load(readLineageId, base ?? document.serverDocument.value),
    installFresh: (fresh) => {
      gateCursor = { cursor: fresh.history_cursor, lineage: fresh.summary.lineage_id };
      document.applyCommandResponse(fresh);
    },
    installMerged: (fresh, merged) => {
      gateCursor = { cursor: fresh.history_cursor, lineage: fresh.summary.lineage_id };
      document.applyCommandResponse(fresh);
      document.installDocument(merged);
    },
    replaceCopy: document.replaceCopy,
    requestStore: () => {
      void history.flush();
    },
    mergeRefusedEdit,
    notifyReloadFailed: () => toast.failure(RELOAD_FAILURE_COPY),
    timer: createSyncGateTimer(),
  });

  /**
   * The header's save status through the gate's kept edit: while the gate
   * holds an unstored kept edit, the status keeps `Inte sparat` with the
   * lease reason instead of following the history's cleared step list to
   * `Sparat`. The kept edit clears only when its merged store succeeds, so
   * the status reads `Sparat` again exactly then. No second kept-edit store:
   * this only reads the gate.
   */
  const keptSaveStatus = computed<ExamWorkspaceSaveStatus>(() => {
    if (gate.hasKeptEdit.value) {
      return { state: "unsaved", detail: LEASE_LOST_COPY };
    }
    return history.saveStatus.value;
  });
  const keptSaveText = computed(() => {
    if (keptSaveStatus.value.state === "unsaved") {
      return "Inte sparat";
    }
    return history.saveText.value;
  });
  const historyWithKeptStatus = { ...history, saveStatus: keptSaveStatus, saveText: keptSaveText };

  /**
   * A server command stored a new step: its response already installed the
   * fresh document, so the gate reads only the step list. An initial open of
   * another lineage leaves this to the lineage watcher, which opens the exam
   * in the gate.
   */
  function applyCommandResponse(response: ExamWorkspaceDocumentResponse): void {
    const changed = document.summary.value?.lineage_id !== response.summary.lineage_id;
    if (!changed) {
      gateCursor = { cursor: response.history_cursor, lineage: response.summary.lineage_id };
    }
    document.applyCommandResponse(response);
    if (!changed) {
      gate.foreignCursor(true);
    }
  }

  leaseHolder.session = useExamWorkspaceEditLease({
    guestStorage: lease?.guestStorage,
    isGuest: () => store.guest !== null,
    lineageId,
    now: lease?.now,
    onAcquired: () => gate.leaseAcquired(),
    onTakeoverRequested: () => history.flush(true).then(() => undefined),
    openGuestChannel: lease?.openGuestChannel,
    server: lease?.server,
    tabId: lease?.tabId,
  });

  watch(lineageId, (next) => {
    if (next === null) {
      return;
    }
    // The open response already installed the document; the gate reads the step list.
    gateCursor = null;
    gate.openExam(next, true);
  });

  watch(
    () => leaseHolder.session?.readOnly.value,
    (readOnly) => {
      if (readOnly === undefined) {
        return;
      }
      if (readOnly) {
        gate.leaseLost();
      } else {
        gate.leaseAcquired();
      }
    },
  );

  onScopeDispose(() => {
    gate.dispose();
  });

  /**
   * Ctrl/Cmd+S, and the store-first step of Spara som and exports: store the
   * pending edit as an undo step now. The step store also overwrites the
   * exam file, so this is the whole save.
   */
  async function save(): Promise<boolean> {
    return await history.flush(false);
  }

  /** Spara som: store the pending edit, then copy the working exam under `name`. */
  async function saveAs(name: string) {
    await history.flush(false);
    return await document.saveDocumentAs(name);
  }

  /**
   * The drawer's busy state: a gate fresh load locks inputs through
   * `editingLocked` but never blocks the Öppna drawer, so the replacing lock
   * it holds does not count while the gate loads.
   */
  const isBusy = computed(
    () => document.isOperationBusy.value || (document.isReplacing.value && gate.phase.value !== "loading"),
  );

  return {
    ...document,
    applyCommandResponse,
    history: historyWithKeptStatus,
    isBusy,
    save,
    saveAs,
    selectedParentId,
    structure,
    /** The lease notice reads only this, so `loading` never shows the lease message. */
    leaseReadOnly: gate.leaseReadOnly,
    /** Every input locks while this holds, in `loading` and in `readonly`. */
    editingLocked: gate.editingLocked,
    /** True while `Ta över` waits for the holder to release. */
    takeoverWaiting: leaseHolder.session!.waiting,
    /** Ask for the lease, claim it once free and read the newest state. */
    requestTakeover: () => leaseHolder.session!.requestTakeover(),
    /** The view wires its part-entry selection once the selection composable exists. */
    registerSelectParent: (select: (parentId: string) => void) => {
      selectParent = select;
    },
  };
}
