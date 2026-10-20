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
 *     saved-exams list (`useExamWorkspaceSavedList`), AI suggestion arrivals,
 *     conversion merges and one-question retries through their own composables.
 *   - Reads that replace the copy in `useExamWorkspaceDocumentReplacing`, which holds arrivals and keying.
 *   - Dirty state: the copy differs from the saved exam file (`sameDocument`).
 */

import { computed, ref, shallowRef, watch } from "vue";

import { isApiError } from "../../../api/client";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
  NativeExamItem,
  NativeExamItemKind,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { examWorkspaceAssetUrls } from "./examWorkspaceAssetUrls";
import { sameDocument } from "./examWorkspaceConversionMerge";
import { useExamWorkspaceItemEdits } from "./useExamWorkspaceItemEdits";
import { withReferencedAssetsOnly } from "./examWorkspaceStructure";
import { withRestoredSuggestion } from "./examWorkspaceSuggestionEdits";
import type { ExamWorkspaceStore } from "./examWorkspaceStore";
import { createSyncFence, type FenceToken, type SyncFence } from "./examWorkspaceSyncFence";
import { createDocumentInstalls } from "./useExamWorkspaceDocumentInstalls";
import { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";
import { useExamWorkspaceDocumentFields } from "./useExamWorkspaceDocumentFields";
import { useExamWorkspaceDocumentReplacing } from "./useExamWorkspaceDocumentReplacing";
import { useExamWorkspaceGapKeying } from "./useExamWorkspaceGapKeying";
import { useExamWorkspaceItemRetry } from "./useExamWorkspaceItemRetry";
import { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";
import { useExamWorkspaceRename } from "./useExamWorkspaceRename";
import { RELOAD_FAILURE_COPY, useExamWorkspaceSave } from "./useExamWorkspaceSave";
import { useExamWorkspaceSavedList } from "./useExamWorkspaceSavedList";
import { useExamWorkspaceTitleVerdict } from "./useExamWorkspaceTitleVerdict";

export { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./useExamWorkspaceConversion";

export type { ExamWorkspaceSaveAsOutcome } from "./useExamWorkspaceSave";

const OPEN_FAILURE_COPY = "Det gick inte att öppna provet. Försök igen.";
const OPEN_OUTDATED_COPY = "Provet är sparat i ett äldre format och kan inte öppnas. Importera originalfilen på nytt.";

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
   * The gate's fresh reload for a reload whose generation retired while it
   * waited and whose exam is still the open one. Absent in specs without a
   * gate, whose fence never retires mid-wait.
   */
  requestFreshLoad?: () => void;
};

export function useExamWorkspaceDocument(options: ExamWorkspaceDocumentOptions) {
  const fallbackFence = createSyncFence();
  const toast = useToast();
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
  const { listOrdering, loadSavedDocuments, recordSummary, savedDocuments } =
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
    syncAfterConflict,
  } = useExamWorkspaceConversion(
    () => isBusy.value,
    {
      applyResponse,
      beginDocumentRead,
      beforeFirstRevision: () => {
        selectedItemId.value = null;
      },
      getFence: () => resolveFence(),
      isCurrent,
      isDirty,
      isSaving: () => operationBusy.value,
      serverDocument,
      summary,
      workspaceDocument,
      store,
    },
    (lineageId) => openDocument(lineageId),
  );
  adoptConversionHolder = adoptConversion;
  const arrivals = useExamWorkspaceSaveArrivals({ convertingItemIds, isOpen, workspaceDocument });
  const { applyArrivingSuggestions } = arrivals;
  // While its batches convert, the imported exam is already editable.
  const isOperationBusy = computed(
    () =>
      operationBusy.value ||
      isImporting.value ||
      (isConverting.value && !isEditingConversion.value),
  );
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

  /** The open document's pictures by asset id, for the editor's image atoms. */
  const assetUrls = computed(() =>
    examWorkspaceAssetUrls(store.shared, workspaceDocument.value, summary.value?.lineage_id ?? null),
  );

  /** Whether `opening` is the exam opening in front of the teacher now. */
  function isOpen(opening: ExamWorkspaceOpening): boolean {
    return openExam.value === opening;
  }

  /**
   * Capture rename ordering before the GET and reconcile in its caller's continuation.
   * Installing an opening must not wait an extra microtask: other completions
   * settling in the same turn must already see that the previous opening ended.
   */
  function beginDocumentRead() {
    const reconcile = beginSummaryRead();
    return (response: ExamWorkspaceDocumentResponse): ExamWorkspaceDocumentResponse => ({
      ...response,
      summary: reconcile(response.summary),
    });
  }

  async function openDocument(lineageId: string): Promise<boolean> {
    if (isOperationBusy.value) {
      return false;
    }
    operationBusy.value = true;
    try {
      const fence = resolveFence();
      const token = fence.begin();
      const reconcile = beginDocumentRead();
      const response = reconcile(await store.shared.getExamWorkspaceDocument(lineageId));
      if (!fence.isCurrent(token)) {
        return false;
      }
      selectedItemId.value = null;
      applyResponse(token, response);
      keying.invalidateCopy();
      return true;
    } catch (error) {
      toast.failure(
        isApiError(error) && error.code === "DOCUMENT_SCHEMA_OUTDATED"
          ? OPEN_OUTDATED_COPY
          : OPEN_FAILURE_COPY,
      );
      return false;
    } finally {
      operationBusy.value = false;
    }
  }

  /**
   * Read the exam again. Also the conflict recovery of undo and the server
   * commands. A 409 that arrives while an operation runs no longer skips the
   * reload: it waits for the running operation to end instead. A retired
   * answer installs nothing.
   */
  async function reloadDocument(): Promise<void> {
    const currentSummary = summary.value;
    if (!currentSummary) return;
    const lineageId = currentSummary.lineage_id;
    const fence = resolveFence();
    const token = fence.begin();
    if (isOperationBusy.value) {
      // A busy-time 409 waits for the operation instead of skipping the
      // reload; the watch resolves when the operation clears without a timer.
      await new Promise<void>((resolve) => {
        const stop = watch(isOperationBusy, (busy) => {
          if (!busy) { stop(); resolve(); }
        }, { immediate: true });
      });
    }
    if (!fence.isCurrent(token)) {
      // The wait outlived the generation: when the captured exam is still
      // the open one, its install may hold an older copy, so the gate reads
      // it fresh. Another exam in front drops the reload.
      if (summary.value?.lineage_id === lineageId) {
        options.requestFreshLoad?.();
      }
      return;
    }
    operationBusy.value = true;
    try {
      const reconcile = beginDocumentRead();
      const response = reconcile(
        await store.shared.getExamWorkspaceDocument(lineageId),
      );
      if (!fence.isCurrent(token)) {
        return;
      }
      applyResponse(token, response);
      keying.invalidateCopy();
      replacingScope.replayArrivalsAfterReload();
    } catch {
      toast.failure(RELOAD_FAILURE_COPY);
    } finally {
      operationBusy.value = false;
    }
  }

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
    workspaceDocument.value = withReferencedAssetsOnly({ ...current, items });
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

  const { saveDocumentAs } = useExamWorkspaceSave({
    applyResponse,
    arrivals,
    beginDocumentRead,
    isBusy,
    isCurrent,
    keying,
    operationBusy,
    summary,
    syncAfterConflict,
    workspaceDocument,
    store,
  });

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
    workspaceDocument.value = withReferencedAssetsOnly(edit(current));
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
    isBusy,
    isDirty,
    isOperationBusy,
    isReplacing: computed(() => replacing.value),
    replaceCopy: replacingScope.replaceCopy,
    isOpen,
    loadSavedDocuments,
    noteExportBlockers,
    noteStored,
    notes,
    openDocument,
    openExam: computed(() => openExam.value),
    reloadDocument,
    renameFailure,
    renameFile,
    restoreItemSuggestion,
    retryItem,
    saveDocumentAs,
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
