/**
 * Exam workspace document state.
 *
 * Domain purpose:
 *   Own the open exam: import and reopen exams, edit the working copy with
 *   immutable updates, track dirty and busy state, select a question, and
 *   reconvert one question.
 *
 * Relationships:
 *   - Transport through the exam workspace store; item edits through one patch
 *     path (`useExamWorkspaceItemEdits`, `useExamWorkspaceGapKeying`).
 *   - Reports each teacher edit through `onEdit`, which the undo history
 *     (`useExamWorkspaceHistory`) turns into autosaved steps; installs the
 *     history's steps and the server commands' results. Every confirmed step
 *     also updates the saved baseline through `noteStored`, so dirty means
 *     the copy differs from the exam file.
 *   - The whole-document field commands (exam and part instructions, tags,
 *     printed-total accepts) in `useExamWorkspaceDocumentFields`, built on
 *     `editDocument` here.
 *   - Spara som and stale-save recovery (`useExamWorkspaceSave`), the
 *     saved-exams list, AI suggestion arrivals, conversion merges and
 *     one-question retries through their own composables.
 *   - The open lifecycle (token-held read, rename reconciliation) in
 *     `useExamWorkspaceDocumentOpen`.
 *   - Conflict reload reads in `useExamWorkspaceDocumentReload`, which owns
 *     the busy wait, the fence and lineage guards, and the failure toast.
 *   - Reads that replace the copy in `useExamWorkspaceDocumentReplacing`, which holds arrivals and keying.
 */

import { computed, onScopeDispose, ref, shallowRef, watch } from "vue";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
  NativeExamItem,
  NativeExamItemKind,
} from "../../../api/examWorkspace";
import { examWorkspaceAssetUrls } from "./examWorkspaceAssetUrls";
import { createExamWorkspaceNewPictures } from "./examWorkspaceNewPictures";
import { sameDocument } from "./examWorkspaceConversionMerge";
import { useExamWorkspaceItemEdits } from "./useExamWorkspaceItemEdits";
import { withReferencedAssetsOnly } from "./examWorkspaceStructure";
import { withRestoredSuggestion } from "./examWorkspaceSuggestionEdits";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence, type FenceToken, type SyncFence } from "./examWorkspaceSyncFence";
import { createDocumentInstalls } from "./useExamWorkspaceDocumentInstalls";
import { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";
import { useExamWorkspaceDocumentFields } from "./useExamWorkspaceDocumentFields";
import { useExamWorkspaceDocumentOpen } from "./useExamWorkspaceDocumentOpen";
import { useExamWorkspaceDocumentReload } from "./useExamWorkspaceDocumentReload";
import { useExamWorkspaceDocumentReplacing } from "./useExamWorkspaceDocumentReplacing";
import { useExamWorkspaceGapKeying } from "./useExamWorkspaceGapKeying";
import { useExamWorkspaceImportPoints } from "./useExamWorkspaceImportPoints";
import { useExamWorkspaceItemRetry } from "./useExamWorkspaceItemRetry";
import type { ExamWorkspaceRouteOpenOutcome } from "./examWorkspaceReplacementTypes";
import { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";
import { useExamWorkspaceRename } from "./useExamWorkspaceRename";
import { useExamWorkspaceSave } from "./useExamWorkspaceSave";
import { useExamWorkspaceSavedList } from "./useExamWorkspaceSavedList";
import { useExamWorkspaceTitleVerdict } from "./useExamWorkspaceTitleVerdict";

export { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./useExamWorkspaceConversion";

export type { ExamWorkspaceSaveAsOutcome } from "./useExamWorkspaceSave";

/**
 * One opening of an exam: created when a document of another lineage is
 * installed, kept while revisions of the same lineage replace the copy.
 * Compared by identity, so reopening an exam later is a new opening.
 */
export type ExamWorkspaceOpening = { readonly lineageId: string };

export type ExamWorkspaceDocumentOptions = {
  /**
   * A teacher edit changed the copy; structural edits become an undo step at
   * once. `before` is the copy just before the edit, so pending typing can be
   * stored as its own step first; null when no such copy applies.
   */
  onEdit?: (structural: boolean, before: NativeExamDocument | null) => void;
  /** The store every server call the document owns runs through. */
  store: ExamWorkspaceStore;
  /** True while another tab holds the edit lease: every edit entry refuses. */
  isReadOnly?: () => boolean;
  /** The sync gate's generation owner; every install carries its token. */
  getFence?: () => SyncFence;
  /**
   * Submit a route-open intent to the gate-owned replacement coordinator;
   * reports the routed outcome. Drawer opens, imports and every other
   * document-replacing entry share this entrance with the address.
   */
  submitRoute: (lineageId: string) => Promise<ExamWorkspaceRouteOpenOutcome>;
  /**
   * Record an installed cursor as the gate's own before the open primitive
   * installs it, so the history watcher consumes it instead of retiring the
   * selection's still-current generation as foreign.
   */
  noteInstallingCursor: (lineageId: string, cursor: string) => void;
  /** The edit-lease tab a guest slot replacement writes as. */
  tabId: () => string;
};

export function useExamWorkspaceDocument(options: ExamWorkspaceDocumentOptions) {
  const fallbackFence = createSyncFence();
  const noteEdit = options.onEdit ?? (() => undefined);
  const isReadOnly = options.isReadOnly ?? (() => false);
  const store = options.store;
  const getFence = options.getFence;

  function resolveFence(): SyncFence {
    const fence = getFence?.();
    if (fence) {
      return fence;
    }
    return fallbackFence;
  }

  function isCurrent(token: FenceToken): boolean {
    return resolveFence().isCurrent(token);
  }

  const workspaceDocument = ref<NativeExamDocument | null>(null);
  // The last working response remains the conversion merge base, not the Spara baseline.
  const serverDocument = ref<NativeExamDocument | null>(null);
  const savedDocument = ref<NativeExamDocument | null>(null);
  const summary = ref<ExamWorkspaceDocumentSummary | null>(null);
  /** The server's newest undo step; history commands are guarded by it. */
  const historyCursor = ref<string | null>(null);
  const notes = ref<string[]>([]);
  const openExam = shallowRef<ExamWorkspaceOpening | null>(null);
  const { noteExportBlockers, titleWithoutText } = useExamWorkspaceTitleVerdict(workspaceDocument);
  const isDirty = computed(() => !sameDocument(workspaceDocument.value, savedDocument.value));
  /** The saved version the open copy stands on. */
  const savedRevision = computed(() => savedDocument.value?.revision ?? null);
  const operationBusy = ref(false);
  const selectedItemId = ref<string | null>(null);
  const { forgetSavedDocument, listOrdering, loadSavedDocuments, recordSummary, savedDocuments } =
    useExamWorkspaceSavedList({ beginSummaryRead: () => beginSummaryRead(), teacher: store.teacher });
  let adoptConversionHolder: (response: ExamWorkspaceDocumentResponse) => void = () => undefined;
  let replayHeldHolder: () => void = () => undefined;
  const {
    applyCommandResponse,
    applyResponse,
    noteStored,
  } = createDocumentInstalls({
    adoptConversion: (response) => adoptConversionHolder(response),
    historyCursor,
    isCurrent,
    noteExportBlockers,
    notes,
    openExam,
    recordSummary,
    replayHeld: () => replayHeldHolder(),
    savedDocument,
    selectedItemId,
    serverDocument,
    summary,
    workspaceDocument,
  });
  const openScope = useExamWorkspaceDocumentOpen({
    applyResponse: (token, response) => applyResponse(token, response),
    beginSummaryRead: () => beginSummaryRead(),
    invalidateCopy: () => keying.invalidateCopy(),
    isBlocked: () => isOtherOperationBusy.value,
    isCurrent,
    noteInstallingCursor: (lineageId, cursor) => options.noteInstallingCursor(lineageId, cursor),
    selectedItemId,
    store,
  });
  const { beginDocumentRead, isOpenReading } = openScope;
  /** Every open ends the import-time points check; an import's own open keeps it pending. */
  function openDocument(lineageId: string, token: FenceToken): Promise<ExamWorkspaceRouteOpenOutcome> {
    importPoints.noteOpening(lineageId);
    return openScope.openDocument(lineageId, token);
  }
  const {
    adoptConversion,
    conversionError,
    conversionMessage,
    conversionProgress,
    conversionStatus,
    convertingItemIds,
    importBlocked,
    importDocument,
    isConverting,
    isEditingConversion,
    isImporting,
    retryConversionStatus,
  } = useExamWorkspaceConversion(
    () => isBusy.value,
    {
      applyResponse,
      beginDocumentRead,
      getFence: () => resolveFence(),
      isCurrent,
      isDirty,
      isSaving: () => operationBusy.value,
      serverDocument,
      summary,
      workspaceDocument,
      store,
      tabId: options.tabId,
      noteImportStarted: (lineageId) => importPoints.noteImportStarted(lineageId),
    },
    (lineageId) => options.submitRoute(lineageId),
  );
  adoptConversionHolder = adoptConversion;
  const importPoints = useExamWorkspaceImportPoints({
    lineageId: () => summary.value?.lineage_id ?? null,
    settled: () => !isImporting.value && !isConverting.value,
  });
  const arrivals = useExamWorkspaceSaveArrivals({ convertingItemIds, isOpen, workspaceDocument });
  const { applyArrivingSuggestions } = arrivals;
  // While its batches convert, the imported exam is already editable.
  /** A save, rename, retry, import or conversion holds the document; an open read is not one of them. */
  const copyBusy = ref(false);
  const isOtherOperationBusy = computed(
    () =>
      operationBusy.value ||
      copyBusy.value ||
      isImporting.value ||
      (isConverting.value && !isEditingConversion.value),
  );
  /**
   * True while an operation other than the drawer's own import or conversion
   * blocks opening: a save, rename, retry or Spara som copy, or an open read.
   * Unlike `isOtherOperationBusy` this never counts `isImporting` or
   * `isConverting`; the drawer's own progress shows those instead.
   */
  const isOpenBlockedByOtherOperation = computed(
    () => operationBusy.value || copyBusy.value || isOpenReading.value,
  );
  const isOperationBusy = computed(() => isOtherOperationBusy.value || isOpenReading.value);
  /** An undo, redo or server command is reading the document that replaces the copy. */
  const replacing = ref(false);
  /** No edit, save or reload may start: an operation runs or the copy is about to be replaced. */
  const isBusy = computed(() => isOperationBusy.value || replacing.value);

  const selectedItem = computed<NativeExamItem | null>(() => {
    const current = workspaceDocument.value;
    if (!current || selectedItemId.value === null) {
      return null;
    }
    return current.items.find((item) => item.item_id === selectedItemId.value) ?? null;
  });

  /** Pictures added from files this session, shown before their first save. */
  const newPictures = createExamWorkspaceNewPictures();
  /** A new opening forgets the previous exam's unsaved pictures. */
  watch(openExam, () => newPictures.reset());
  onScopeDispose(() => newPictures.reset());

  /** The open document's pictures by asset id, for the editor's image atoms. */
  const assetUrls = computed(() => ({
    ...examWorkspaceAssetUrls(store.shared, workspaceDocument.value, summary.value?.lineage_id ?? null),
    ...newPictures.urls.value,
  }));

  /** Whether `opening` is the exam opening in front of the teacher now. */
  function isOpen(opening: ExamWorkspaceOpening): boolean {
    return openExam.value === opening;
  }

  // Conflict reload reads; later-defined keying and arrival replay arrive
  // as closures, as the open scope already does with `keying`.
  const { reloadDocument } = useExamWorkspaceDocumentReload({
    summary,
    resolveFence,
    isOperationBusy,
    operationBusy,
    beginDocumentRead,
    store,
    applyResponse,
    invalidateCopy: () => keying.invalidateCopy(),
    replayArrivalsAfterReload: () => replacingScope.replayArrivalsAfterReload(),
  });

  function selectItem(itemId: string): void {
    selectedItemId.value = itemId;
  }

  function setTitle(title: string): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value || isReadOnly()) return;
    workspaceDocument.value = { ...current, title };
    noteEdit(false, current);
  }

  const { beginSummaryRead, renameFailure, renameFile } = useExamWorkspaceRename({
    isBusy: () => isBusy.value,
    operationBusy,
    summary,
    savedDocuments,
    teacher: store.teacher,
  });

  const { retryItem: requestItemRetry } = useExamWorkspaceItemRetry({
    getFence: () => resolveFence(),
    isBusy: () => isBusy.value,
    isCurrent,
    openExam,
    operationBusy,
    serverDocument,
    summary,
    workspaceDocument,
    teacher: store.teacher,
  });

  /** Retry one question, and drop in-flight keying replies for the item it replaced. */
  async function retryItem(itemId: string, kind: NativeExamItemKind): Promise<void> {
    if (isReadOnly()) return;
    const prior = workspaceDocument.value;
    const applied = await requestItemRetry(itemId, kind);
    if (applied) {
      keying.invalidateItem(itemId);
      noteEdit(true, prior);
    }
  }

  /**
   * The one path every item edit takes; a placeholder whose batch still converts is refused.
   * A picture the edit removed takes its asset record with it.
   */
  function patchItem(
    itemId: string,
    patch: (item: NativeExamItem) => NativeExamItem,
    structural = false,
  ): boolean {
    const current = workspaceDocument.value;
    if (!current || isBusy.value || isReadOnly() || convertingItemIds.value.has(itemId)) {
      return false;
    }
    let changed = false;
    const items = current.items.map((item) => {
      if (item.item_id !== itemId) {
        return item;
      }
      changed = true;
      return patch(item);
    });
    if (!changed) {
      return false;
    }
    workspaceDocument.value = withReferencedAssetsOnly(newPictures.withDeclared({ ...current, items }));
    noteEdit(structural, current);
    return true;
  }

  // Every gap keying edit and its asynchronous misspelling reply.
  const keying = useExamWorkspaceGapKeying({ openExam, patchItem, workspaceDocument, shared: store.shared });

  // Reads that replace the open copy (undo, redo, server commands).
  const replacingScope = useExamWorkspaceDocumentReplacing({
    workspaceDocument,
    selectedItemId,
    replacing,
    arrivals,
    keying,
    isCurrent,
  });
  replayHeldHolder = () => replacingScope.replayHeld();

  const { beginCopy, beginNewExam } = useExamWorkspaceSave({
    copyBusy,
    getFence: () => resolveFence(),
    historyCursor,
    isBusy,
    summary,
    store,
    workspaceDocument,
  });

  /**
   * Install a replacement response for the selection's token: the selected
   * question clears and the fresh copy lands with its keying dropped. The
   * coordinator admits this only while its intent is still desired and its
   * token is current; the read itself decides nothing about address or
   * recovery.
   */
  function installReplacementDocument(
    token: FenceToken,
    response: ExamWorkspaceDocumentResponse,
  ): void {
    selectedItemId.value = null;
    applyResponse(token, response);
    keying.invalidateCopy();
  }

  // Every teacher edit command, applied through the one patch path above.
  const itemEdits = useExamWorkspaceItemEdits(patchItem);

  function restoreItemSuggestion(itemId: string): void {
    patchItem(itemId, (item) => withRestoredSuggestion(item));
  }

  /**
   * An edit of the whole copy. A structural edit (add, delete, reorder) is one
   * undo step at once; typing waits for the pause like an item's text.
   */
  function editDocument(
    edit: (document: NativeExamDocument) => NativeExamDocument,
    selectId: string | null = null,
    structural = true,
  ): boolean {
    const current = workspaceDocument.value;
    if (!current || isBusy.value || isReadOnly()) {
      return false;
    }
    workspaceDocument.value = withReferencedAssetsOnly(newPictures.withDeclared(edit(current)));
    if (selectId !== null) {
      selectedItemId.value = selectId;
    }
    noteEdit(structural, current);
    return true;
  }

  // The whole-document field commands, each one `editDocument` call.
  const fieldCommands = useExamWorkspaceDocumentFields({
    courseKey: () => workspaceDocument.value?.header.course?.key ?? null,
    editDocument,
  });

  return {
    ...itemEdits,
    ...fieldCommands,
    applyCommandResponse,
    editDocument,
    forgetSavedDocument,
    historyCursor,
    installDocument: replacingScope.installDocument,
    listOrdering,
    applyArrivingSuggestions,
    assetUrls,
    conversionError,
    conversionMessage,
    conversionProgress,
    conversionStatus,
    convertingItemIds,
    isConverting,
    retryConversionStatus,
    importBlocked,
    importDocument,
    /** Right after an import here, its points check shows until Avfärda or the next open (TASK-SKRIPT-40-04-23). */
    importPointsShown: importPoints.shown,
    dismissImportPoints: importPoints.dismiss,
    isBusy,
    isDirty,
    isOpenBlockedByOtherOperation,
    isOperationBusy,
    isReplacing: computed(() => replacing.value),
    replaceCopy: replacingScope.replaceCopy,
    isOpen,
    loadSavedDocuments,
    noteExportBlockers,
    noteStored,
    notes,
    newPictures,
    openDocument,
    openExam: computed(() => openExam.value),
    reloadDocument,
    renameFailure,
    renameFile,
    restoreItemSuggestion,
    retryItem,
    beginCopy,
    beginNewExam,
    installReplacementDocument,
    releaseCopyBusy: () => {
      copyBusy.value = false;
    },
    savedDocuments,
    savedRevision,
    serverDocument,
    selectItem,
    setTitle,
    selectedItem,
    selectedItemId,
    summary,
    titleWithoutText,
    updateItemGapValues: keying.updateItemGapValues,
    removeItemAutomaticValue: keying.removeItemAutomaticValue,
    workspaceDocument,
  };
}
