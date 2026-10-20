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
 *   the gate as `leaseLost`, a refused open claim as `leaseRefused`, a
 *   stale-cursor 409 as `staleConflict`, and a held lease as `leaseAcquired`.
 *   A load that finishes while the open claim is still in flight keeps
 *   `loading` until the claim decides. It owns `selectedParentId` (the part
 *   entry the teacher selected) so structural inserts land after the
 *   selected part; the selection composable drives it.
 *
 * Relationships:
 *   - Composes `useExamWorkspaceDocument`, `useExamWorkspaceHistory`,
 *     `useExamWorkspaceStructure` and `useExamWorkspaceSyncGate`; consumed
 *     by `ExamWorkspaceView`.
 */

import { computed, onScopeDispose, ref } from "vue";

import type { ExamWorkspaceDocumentResponse, NativeExamDocument } from "../../../api/examWorkspace";
import type { ExamWorkspaceUnreadableDocument } from "../../../api/examWorkspaceUnreadableFiles";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { useToast } from "../../../composables/useToast";
import { mergeRefusedEdit } from "./examWorkspaceRefusedEditMerge";
import { createFencedTransport } from "./examWorkspaceFencedTransport";
import { OPEN_FAILURE_COPY } from "./useExamWorkspaceDocumentOpen";
import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceReplacementTypes";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import {
  useExamWorkspaceUnreadableFiles,
  type UnreadableFilesState,
} from "./useExamWorkspaceUnreadableFiles";
import {
  useExamWorkspaceEditLease,
  type ExamWorkspaceEditLeaseDeps,
} from "./useExamWorkspaceEditLease";
import { useExamWorkspaceHistory } from "./useExamWorkspaceHistory";
import { readStepList } from "./useExamWorkspaceHistoryLoader";
import type { FenceToken } from "./examWorkspaceSyncFence";
import type { ExamWorkspaceRouteProjection } from "./examWorkspaceRouteProjection";
import { createSyncGateTimer } from "./examWorkspaceSyncGateTimer";
import { useExamWorkspaceSyncGate } from "./useExamWorkspaceSyncGate";
import { useExamWorkspaceStructure } from "./useExamWorkspaceStructure";
import { RELOAD_FAILURE_COPY, SAVE_AS_FAILURE_COPY } from "./useExamWorkspaceSave";

/** The lease seams specs override; production uses the transport and the browser slot. */
export type ExamWorkspaceEditingLeaseOverrides = Partial<
  Pick<
    ExamWorkspaceEditLeaseDeps,
    "guestStorage" | "now" | "openGuestChannel" | "server" | "tabId"
  >
>;

export function useExamWorkspaceEditing(
  store: ExamWorkspaceStore,
  projection: ExamWorkspaceRouteProjection,
  lease?: ExamWorkspaceEditingLeaseOverrides,
) {
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
  let gate: ReturnType<typeof useExamWorkspaceSyncGate> | null = null;
  function requireGate(): ReturnType<typeof useExamWorkspaceSyncGate> {
    if (!gate) {
      throw new Error("expected the sync gate");
    }
    return gate;
  }
  const fenced = createFencedTransport(() => requireGate().fence, store.shared);
  const document = useExamWorkspaceDocument({
    getFence: () => requireGate().fence,
    isReadOnly: () => requireGate().editingLocked.value,
    noteInstallingCursor: (lineageId, cursor) => {
      gateCursor = { cursor, lineage: lineageId };
    },
    onEdit: (structural, before) => noteEdit(structural, before),
    store,
    submitRoute: (lineageId) => requireGate().submitRoute(lineageId),
  });
  const lineageId = () => document.summary.value?.lineage_id ?? null;

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
    const saved = document.savedDocuments.value.find((entry) => entry.lineage_id === lineage);
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
    if (store.teacher === null) {
      toast.failure(OPEN_FAILURE_COPY);
      return;
    }
    await unreadableFiles.load();
    if (unreadableFiles.files.value.some((entry) => entry.lineage_id === lineage)) {
      unreadableTarget.value = lineage;
      return;
    }
    await document.loadSavedDocuments();
    if (document.savedDocuments.value.some((entry) => entry.lineage_id === lineage)) {
      unreadableTarget.value = lineage;
      return;
    }
    toast.failure(OPEN_FAILURE_COPY);
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
    await document.loadSavedDocuments();
    const removed =
      !unreadableFiles.files.value.some((entry) => entry.lineage_id === lineage) &&
      !document.savedDocuments.value.some((entry) => entry.lineage_id === lineage);
    if (removed) {
      unreadableTarget.value = null;
    }
  }

  /**
   * Read and install the named document for the selection's token: the only
   * open path. An installed open clears the unreadable notice, whatever it
   * reported before.
   */
  async function openRouteTarget(lineage: string, token: FenceToken): Promise<ExamWorkspaceRouteOpenOutcome> {
    const outcome = await document.openDocument(lineage, token);
    if (outcome === "installed") {
      unreadableTarget.value = null;
    }
    return outcome;
  }

  /**
   * A server command stored a new step: its response already installed the
   * fresh document, so the gate reads only the step list. A response for
   * another lineage adopts it explicitly like a selected opening: the gate
   * opens the exam with a step-list load and the lease claims it, retiring
   * the previous generation first. Coordinator selections never pass through
   * here; they install through the fenced primitive instead. A retired token
   * installs nothing and reports nothing back.
   */
  function applyCommandResponse(token: FenceToken, response: ExamWorkspaceDocumentResponse): void {
    const current = requireGate();
    if (!current.fence.isCurrent(token)) {
      return;
    }
    const changed = document.summary.value?.lineage_id !== response.summary.lineage_id;
    if (!changed) {
      gateCursor = { cursor: response.history_cursor, lineage: response.summary.lineage_id };
    }
    document.applyCommandResponse(token, response);
    if (!changed) {
      current.foreignCursor(true);
      return;
    }
    gateCursor = null;
    current.openExam(response.summary.lineage_id, true);
    leaseHolder.session?.openLineage(response.summary.lineage_id);
  }

  const history = useExamWorkspaceHistory({
    historyCursor: document.historyCursor,
    install: document.installDocument,
    isReadOnly: () => requireGate().editingLocked.value,
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
      requireGate().foreignCursor(true);
      return false;
    },
    noteGateStored: (token) => requireGate().noteStored(token),
    keptUnstored: () => requireGate().hasKeptEdit.value,
    noteLeaseLost: () => leaseHolder.session?.noteLostLease(),
    noteStored: document.noteStored,
    isGuest: () => store.guest !== null,
    onConflict: () => {
      requireGate().staleConflict();
      return Promise.resolve();
    },
    replaceCopy: document.replaceCopy,
    savedRevision: () => document.savedRevision.value,
    enqueueWrite: (run, refused) => requireGate().enqueueWrite(run, refused),
    isCurrent: (token) => requireGate().fence.isCurrent(token),
    transport: fenced,
    tabId: () => leaseHolder.session?.tabId ?? "",
    workspaceDocument: document.workspaceDocument,
  });
  noteEdit = history.noteEdit;

  const structure = useExamWorkspaceStructure({
    applyCommandResponse: (token, response) => applyCommandResponse(token, response),
    editDocument: document.editDocument,
    enqueueWrite: (run, refused) => requireGate().enqueueWrite(run, refused),
    flush: history.flush,
    historyCursor: document.historyCursor,
    isBusy: () => document.isBusy.value || history.storing.value,
    isCurrent: (token) => requireGate().fence.isCurrent(token),
    isReadOnly: () => requireGate().editingLocked.value,
    lineageId,
    noteLeaseLost: () => leaseHolder.session?.noteLostLease(),
    onConflict: () => {
      requireGate().staleConflict();
      return Promise.resolve();
    },
    replaceCopy: document.replaceCopy,
    savedRevision: () => document.savedRevision.value,
    selectItem: document.selectItem,
    selectParent: (parentId) => selectParent(parentId),
    selectedItemId: document.selectedItemId,
    selectedParentId,
    transport: fenced,
    tabId: () => leaseHolder.session?.tabId ?? "",
    workspaceDocument: document.workspaceDocument,
  });

  gate = useExamWorkspaceSyncGate({
    abandonAttempt: () => history.abandonAttempt(),
    beginCopy: (sourceLineageId, name) => document.beginCopy(sourceLineageId, name),
    claimSelectedLease: (nextLineageId) => {
      leaseHolder.session?.openLineage(nextLineageId);
    },
    confirmedCopy: () => history.confirmedCopy(),
    desiredCopy: () => history.desiredCopy(),
    hasActiveStore: () => history.storing.value,
    hasUnconfirmed: () => history.hasUnconfirmed.value,
    installedSource: () => document.summary.value?.lineage_id ?? null,
    installReplacementDocument: (token, response) => {
      // The coordinator's selected install carries the gate's own cursor: the
      // history watcher must consume it, not report it back as foreign (which
      // would retire the selection's still-current generation).
      gateCursor = { cursor: response.history_cursor, lineage: response.summary.lineage_id };
      document.installReplacementDocument(token, response);
    },
    isVisibleDirty: () => document.isDirty.value,
    notifyCopyFailed: () => toast.failure(SAVE_AS_FAILURE_COPY),
    notifyRouteFailed: () => toast.failure(OPEN_FAILURE_COPY),
    notifyRouteUnreadable: (lineage) => {
      void noteRouteUnreadable(lineage);
    },
    openRouteTarget: (nextLineageId, token) => openRouteTarget(nextLineageId, token),
    projectAddress: (nextLineageId) => projection.project(nextLineageId),
    releaseCopyBusy: () => document.releaseCopyBusy(),
    waitForRouterIdle: () => projection.waitForIdle(),
    isLeaseHeld: () => leaseHolder.session !== null && !leaseHolder.session.readOnly.value,
    isOpenClaimPending: () => leaseHolder.session?.isOpenClaimPending() ?? false,
    publishedPieces: () => history.publishedPieces(),
    resetUnconfirmed: () => history.resetUnconfirmed(),
    settleEdit: () => history.flush(true),
    dropOwedSnapshots: () => history.dropOwedSnapshots(),
    readDocument: (readLineageId) => store.shared.getExamWorkspaceDocument(readLineageId),
    readStepList: (readLineageId) => readStepList(store.shared, readLineageId),
    applyStepList: (token, read, base) => history.applySteps(token, read, base ?? document.serverDocument.value),
    resetStepList: (token) => history.resetSteps(token),
    installFresh: (token, fresh) => {
      if (!requireGate().fence.isCurrent(token)) {
        return;
      }
      gateCursor = { cursor: fresh.history_cursor, lineage: fresh.summary.lineage_id };
      document.applyCommandResponse(token, fresh);
    },
    installMerged: (token, fresh, merged) => {
      if (!requireGate().fence.isCurrent(token)) {
        return;
      }
      gateCursor = { cursor: fresh.history_cursor, lineage: fresh.summary.lineage_id };
      document.applyCommandResponse(token, fresh);
      document.installDocument(token, merged);
    },
    replaceCopy: document.replaceCopy,
    requestStore: () => {
      void history.flush();
    },
    mergeRefusedEdit,
    notifyReloadFailed: () => toast.failure(RELOAD_FAILURE_COPY),
    timer: createSyncGateTimer(),
  });

  const leaseSession = useExamWorkspaceEditLease({
    fence: requireGate().fence,
    guestStorage: lease?.guestStorage,
    isGuest: () => store.guest !== null,
    lineageId,
    now: lease?.now,
    onLeaseAcquired: () => requireGate().leaseAcquired(),
    onLeaseLost: () => requireGate().leaseLost(),
    onLeaseRefused: () => requireGate().leaseRefused(),
    onPageHidden: () => requireGate().pageHidden(),
    onTakeoverRequested: () => history.flush(true).then(() => undefined),
    openGuestChannel: lease?.openGuestChannel,
    server: lease?.server,
    tabId: lease?.tabId,
  });
  leaseHolder.session = leaseSession;

  onScopeDispose(() => {
    requireGate().dispose();
  });

  /**
   * Ctrl/Cmd+S, and the store-first step of Spara som and exports: store the
   * pending edit as an undo step now. The step store also overwrites the
   * exam file, so this is the whole save.
   */
  async function save(): Promise<boolean> {
    return await history.flush(false);
  }

  /** Spara som: register the copy intent with the coordinator before its first
   * await, sharing the source barrier; the coordinator admits the copy result
   * only while its intent is still desired and its token is current. */
  async function saveAs(name: string) {
    return requireGate().submitSaveAs(name);
  }

  /**
   * The drawer's busy state: a gate fresh load locks inputs through
   * `editingLocked` but never blocks the Öppna drawer, so the replacing lock
   * it holds does not count while the gate loads.
   */
  const gateForBusy = () => gate;
  const isBusy = computed(
    () => document.isOperationBusy.value || (document.isReplacing.value && (gateForBusy()?.phase.value ?? "loading") !== "loading"),
  );

  return {
    ...document,
    applyCommandResponse: (response: ExamWorkspaceDocumentResponse) => {
      const current = requireGate();
      const token = current.fence.begin();
      applyCommandResponse(token, response);
    },
    history,
    isBusy,
    save,
    saveAs,
    selectedParentId,
    structure,
    /** The lease notice reads only this, so `loading` never shows the lease message. */
    leaseReadOnly: requireGate().leaseReadOnly,
    /** Every input locks while this holds, in `loading` and in `readonly`. */
    editingLocked: requireGate().editingLocked,
    /** True while `Ta över` waits for the holder to release. */
    takeoverWaiting: leaseSession.waiting,
    /** Ask for the lease, claim it once free and read the newest state. */
    requestTakeover: () => leaseSession.requestTakeover(),
    /** The view wires its part-entry selection once the selection composable exists. */
    registerSelectParent: (select: (parentId: string) => void) => {
      selectParent = select;
    },
    /** Submit a route-open intent to the gate-owned replacement coordinator. */
    requestRoute: (lineageId: string) => requireGate().submitRoute(lineageId),
    /** The address the coordinator stands behind: its desired target, else its source. */
    currentRouteAddress: () => requireGate().currentAddress(),
    /** The shared router adapter: observed by the address, published only by the coordinator. */
    routeProjection: projection,
    /** A saved exam the app could not open: the notice owns this lineage until
     * an installed open or a successful remove clears it. */
    unreadableTarget,
    /** The shared unreadable-files list the Öppna drawer rows render too. */
    unreadableFiles,
    /** True while the unreadable target's own download or remove runs. */
    unreadableTargetBusy,
    /** Download the notice's stored file unchanged through the shared path. */
    downloadUnreadableTarget,
    /** Move the notice's stored file to the papperskorg and reload the lists. */
    removeUnreadableTarget,
  };
}
