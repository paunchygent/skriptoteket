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
import { useExamWorkspaceKeptEdit } from "./useExamWorkspaceKeptEdit";
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
  // The kept refused edit, whether this session may still install or store
  // past an await, and the in-flight recoveries disposal or an exam change
  // must settle: the routine rechecks disposal and lineage before and after
  // every await and registers no watcher, so no watcher outlives the editor
  // and every path settles.
  const keptEdit = useExamWorkspaceKeptEdit();
  let disposed = false;
  const recoveryAborters = new Set<() => void>();
  function settleRecoveryAborters(): void {
    for (const abort of [...recoveryAborters]) {
      abort();
    }
    recoveryAborters.clear();
  }
  onScopeDispose(() => {
    disposed = true;
    keptEdit.clear();
    settleRecoveryAborters();
  });
  watch(lineageId, () => {
    keptEdit.clear();
    settleRecoveryAborters();
  });

  /**
   * Await `work`, but let disposal or an exam change settle it as null
   * instead of leaving the recovery parked: a history read that never
   * answers must not outlive the exam it was read for. Never registers
   * anything after disposal.
   */
  function abortable<T>(work: Promise<T>): Promise<T | null> {
    if (disposed) {
      return Promise.resolve(null);
    }
    return new Promise<T | null>((resolve) => {
      const abort = (): void => {
        recoveryAborters.delete(abort);
        resolve(null);
      };
      recoveryAborters.add(abort);
      work.then(
        (value) => {
          recoveryAborters.delete(abort);
          resolve(value);
        },
        () => {
          recoveryAborters.delete(abort);
          resolve(null);
        },
      );
    });
  }

  /**
   * Merge a kept refused edit onto the newest server document and store it
   * through the normal save path (TASK-SKRIPT-40-04-14, USER decision
   * 2026-10-19 "Ta över keeps the edit"): capture the pending working copy,
   * reload, then await the history's own load for that lineage — which also
   * synchronizes when the cursor is unchanged and the GET returned a fresh
   * object — and merge with mergeRefusedEdit. A failed reload keeps the
   * recovery set and the edit visible and pending; disposal or a lineage
   * change stops the routine without installing or storing. A refused save
   * or a failed store keeps the existing status and toasts.
   */
  async function recoverKeptEdit(startLineage: string, awaitStore: boolean): Promise<void> {
    if (disposed || lineageId() !== startLineage) {
      return;
    }
    const edited = history.pending.value ? document.workspaceDocument.value : null;
    const base = keptEdit.get();
    if (edited === null || base === null) {
      return;
    }
    const startServer = document.serverDocument.value;
    await abortable(reload());
    if (disposed || lineageId() !== startLineage) {
      return;
    }
    // reloadDocument catches its own failure and only toasts, so an unchanged
    // server document means the reload failed: keep the recovery set and the
    // refused edit pending without merging or storing.
    if (document.serverDocument.value === startServer) {
      return;
    }
    const synced = await abortable(history.load(startLineage));
    if (disposed || lineageId() !== startLineage || synced !== true) {
      return;
    }
    const newest = document.workspaceDocument.value;
    if (disposed || lineageId() !== startLineage || newest === null) {
      return;
    }
    const merged = mergeRefusedEdit(base, edited, newest);
    if (merged === null) {
      keptEdit.clear();
      return;
    }
    await abortable(
      document.replaceCopy(async () => {
        document.installDocument(merged);
      }),
    );
    if (disposed || lineageId() !== startLineage) {
      return;
    }
    if (awaitStore) {
      if (await abortable(history.flush())) {
        keptEdit.clear();
      }
      return;
    }
    // Inside the history's own 409 handling its flush queue is still running:
    // queue the merged store without awaiting it, so the outer store cannot
    // deadlock on the queue it already holds.
    void history.flush().then((stored) => {
      if (stored) {
        keptEdit.clear();
      }
    });
  }

  /**
   * A refused edit survives the takeover: keep its step document as the
   * recovery base while a pending edit stands, then always read the newest
   * server document: with a kept refused edit the recovery routine merges it
   * onto the newest copy, without one the reload alone replaces the stale
   * copy a read-only tab shows. Before KE the acquisition always reloaded,
   * so a tab that gets the lease with nothing pending reads the newest
   * state instead of keeping its stale copy.
   */
  async function acquireWithKeptEdit(): Promise<void> {
    const startLineage = lineageId();
    if (disposed || startLineage === null) {
      return;
    }
    if (history.pending.value) {
      const base = history.stepDocument.value;
      if (base !== null) {
        keptEdit.set(base);
      }
    }
    if (keptEdit.get() !== null && history.pending.value) {
      await recoverKeptEdit(startLineage, true);
      return;
    }
    await reload();
  }

  /**
   * The 409 conflict path while a refused edit is recovering: run the same
   * recovery routine instead of reloading past the edit, so a later save
   * after a failed reload merges the edit onto the newest copy. A reload
   * failure keeps the recovery set and the edit visible and pending.
   */
  async function handleConflict(): Promise<void> {
    const startLineage = lineageId();
    if (!disposed && startLineage !== null && keptEdit.get() !== null && history.pending.value) {
      await recoverKeptEdit(startLineage, false);
      return;
    }
    await reload();
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
    onConflict: handleConflict,
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
    onConflict: handleConflict,
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
