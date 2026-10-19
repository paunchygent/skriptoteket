/**
 * Exam workspace editing session.
 *
 * Domain purpose:
 *   Join the open exam, its server-stored undo history and the structure
 *   commands into one editing session: every teacher edit becomes an undo
 *   step through a 900 ms pause or at once, and the step store also writes
 *   the exam file (TASK-SKRIPT-40-04-14, one save model). Only the tab that
 *   holds the edit lease writes: a tab without it is read-only, every write
 *   carries the tab id, and a write refused with `EDIT_LEASE_HELD` turns
 *   read-only while the pending edit stays visible. It
 *   owns `selectedParentId` (the part entry the teacher selected) so structural
 *   inserts land after the selected part; the selection composable drives it.
 *
 * Relationships:
 *   - Composes `useExamWorkspaceDocument`, `useExamWorkspaceHistory` and
 *     `useExamWorkspaceStructure`; consumed by `ExamWorkspaceView`.
 */

import { onScopeDispose, ref, watch } from "vue";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { mergeRefusedEdit } from "./examWorkspaceRefusedEditMerge";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import {
  useExamWorkspaceEditLease,
  type ExamWorkspaceEditLeaseDeps,
} from "./useExamWorkspaceEditLease";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";

/** The lease seams specs override; production uses the transport and the browser slot. */
export type ExamWorkspaceEditingLeaseOverrides = Partial<
  Pick<
    ExamWorkspaceEditLeaseDeps,
    "guestStorage" | "now" | "openGuestChannel" | "server" | "tabId"
  >
>;

export function useExamWorkspaceEditing(store: ExamWorkspaceStore, lease?: ExamWorkspaceEditingLeaseOverrides) {
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
  const document = useExamWorkspaceDocument({
    isReadOnly: () => leaseHolder.session?.readOnly.value ?? true,
    onEdit: (structural, before) => noteEdit(structural, before),
    store,
  });
  const lineageId = () => document.summary.value?.lineage_id ?? null;
  const reload = () => document.reloadDocument();
  // Waits started in async continuations have no active effect scope left for
  // onScopeDispose, so disposal notifiers registered here settle them instead.
  const disposeNotifiers = new Set<() => void>();
  onScopeDispose(() => {
    for (const notify of [...disposeNotifiers]) {
      notify();
    }
    disposeNotifiers.clear();
  });

  /**
   * After a reload the history loads the fresh step list; wait until its step
   * matches the reloaded server copy (or the load failed and cleared it), so
   * the merged edit's flush carries the fresh position instead of truncating
   * the other tab's steps after a stale one. The wait always settles: a
   * lineage that moved on or a disposed scope resolves stale (false) so the
   * merge is skipped instead of leaking the watch or merging onto the wrong
   * exam.
   */
  function waitForHistoryStep(startLineage: string | null): Promise<boolean> {
    const server = document.serverDocument.value;
    if (server === null || history.stepDocument.value === server || history.stepDocument.value === null) {
      return Promise.resolve(lineageId() === startLineage);
    }
    return new Promise<boolean>((resolve) => {
      let settled = false;
      let stopStep: () => void = () => undefined;
      let stopLineage: () => void = () => undefined;
      const finish = (ready: boolean) => {
        if (settled) {
          return;
        }
        settled = true;
        disposeNotifiers.delete(onDispose);
        stopStep();
        stopLineage();
        resolve(ready);
      };
      stopStep = watch(history.stepDocument, (step) => {
        if (step === document.serverDocument.value || step === null) {
          finish(lineageId() === startLineage);
        }
      });
      stopLineage = watch(lineageId, (next) => {
        if (next !== startLineage) {
          finish(false);
        }
      });
      const onDispose = () => finish(false);
      disposeNotifiers.add(onDispose);
    });
  }

  /**
   * A refused edit survives the takeover (TASK-SKRIPT-40-04-14, USER decision
   * 2026-10-19 "Ta över keeps the edit"): capture the pending edit against
   * its step before the reload replaces the working copy, then merge it onto
   * the newest server document and store it through the normal save path. A
   * refused save or a failed store keeps the existing status and toasts.
   */
  async function acquireWithKeptEdit(): Promise<void> {
    const edited = history.pending.value ? document.workspaceDocument.value : null;
    const base = edited === null ? null : history.stepDocument.value;
    const startServer = document.serverDocument.value;
    const startLineage = lineageId();
    await reload();
    if (edited === null || base === null) {
      return;
    }
    // reloadDocument catches its own failure and only toasts, so an unchanged
    // server document means the reload failed: keep the refused edit pending
    // without merging or storing.
    if (document.serverDocument.value === startServer) {
      return;
    }
    const ready = await waitForHistoryStep(startLineage);
    if (!ready) {
      return;
    }
    const newest = document.workspaceDocument.value;
    if (newest === null) {
      return;
    }
    const merged = mergeRefusedEdit(base, edited, newest);
    if (merged === null) {
      return;
    }
    await document.replaceCopy(async () => {
      document.installDocument(merged);
    });
    await history.flush();
  }

  const history = useExamWorkspaceHistory({
    historyCursor: document.historyCursor,
    install: document.installDocument,
    isReadOnly: () => leaseHolder.session?.readOnly.value ?? true,
    isReplacing: () => document.isReplacing.value,
    // Not `isBusy`: that includes the replacing lock the history's own reads hold.
    isBlocked: () => document.isOperationBusy.value,
    lineageId,
    noteExportBlockers: document.noteExportBlockers,
    noteLeaseLost: () => leaseHolder.session?.noteLostLease(),
    noteStored: document.noteStored,
    isGuest: () => store.guest !== null,
    onConflict: reload,
    replaceCopy: document.replaceCopy,
    savedRevision: () => document.savedRevision.value,
    serverDocument: document.serverDocument,
    shared: store.shared,
    tabId: () => leaseHolder.session?.tabId ?? "",
    workspaceDocument: document.workspaceDocument,
  });
  noteEdit = history.noteEdit;

  const structure = useExamWorkspaceStructure({
    applyCommandResponse: document.applyCommandResponse,
    editDocument: document.editDocument,
    flush: history.flush,
    historyCursor: document.historyCursor,
    isBusy: () => document.isBusy.value || history.storing.value,
    isReadOnly: () => leaseHolder.session?.readOnly.value ?? true,
    lineageId,
    noteLeaseLost: () => leaseHolder.session?.noteLostLease(),
    onConflict: reload,
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

  leaseHolder.session = useExamWorkspaceEditLease({
    guestStorage: lease?.guestStorage,
    isGuest: () => store.guest !== null,
    lineageId,
    now: lease?.now,
    onAcquired: () => acquireWithKeptEdit(),
    onTakeoverRequested: () => history.flush(true).then(() => undefined),
    openGuestChannel: lease?.openGuestChannel,
    server: lease?.server,
    tabId: lease?.tabId,
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

  return {
    ...document,
    history,
    save,
    saveAs,
    selectedParentId,
    structure,
    /** The edit lease: read-only while another tab holds the exam. */
    readOnly: leaseHolder.session!.readOnly,
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
