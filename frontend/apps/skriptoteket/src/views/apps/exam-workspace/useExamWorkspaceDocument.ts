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
  ExamCourseChoice,
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
};

export function useExamWorkspaceDocument(options: ExamWorkspaceDocumentOptions) {
  const toast = useToast();
  const noteEdit = options.onEdit ?? (() => undefined);
  const isReadOnly = options.isReadOnly ?? (() => false);
  const store = options.store;

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
      isDirty,
      isSaving: () => operationBusy.value,
      serverDocument,
      summary,
      workspaceDocument,
      store,
    },
    (lineageId) => openDocument(lineageId),
  );
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

  function applyResponse(
    response: ExamWorkspaceDocumentResponse,
    local: NativeExamDocument = response.document,
  ): void {
    if (openExam.value?.lineageId !== response.summary.lineage_id) {
      openExam.value = { lineageId: response.summary.lineage_id };
    }
    workspaceDocument.value = local;
    noteExportBlockers(response.document.title, response.export_blockers);
    serverDocument.value = response.document;
    savedDocument.value = response.saved_document;
    summary.value = response.summary;
    historyCursor.value = response.history_cursor;
    recordSummary(response.summary);
    notes.value = response.notes;
    adoptConversion(response);
    const items = local.items;
    selectedItemId.value = items.some((item) => item.item_id === selectedItemId.value)
      ? selectedItemId.value
      : (items[0]?.item_id ?? null);
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
    if (isBusy.value) {
      return false;
    }
    operationBusy.value = true;
    try {
      const reconcile = beginDocumentRead();
      const response = reconcile(await store.shared.getExamWorkspaceDocument(lineageId));
      selectedItemId.value = null;
      applyResponse(response);
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
   * reload: it waits for the running operation to end instead.
   */
  async function reloadDocument(): Promise<void> {
    const currentSummary = summary.value;
    if (!currentSummary) return;
    if (isOperationBusy.value) {
      // A busy-time 409 waits for the operation instead of skipping the
      // reload; the watch resolves when the operation clears without a timer.
      await new Promise<void>((resolve) => {
        const stop = watch(isOperationBusy, (busy) => {
          if (!busy) { stop(); resolve(); }
        }, { immediate: true });
      });
    }
    operationBusy.value = true;
    try {
      const reconcile = beginDocumentRead();
      const response = reconcile(await store.shared.getExamWorkspaceDocument(currentSummary.lineage_id));
      applyResponse(response);
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

  function setCourse(course: ExamCourseChoice | null): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value || isReadOnly()) return;
    workspaceDocument.value = { ...current, header: { ...current.header, course } };
    noteEdit(true, current);
  }

  const { beginSummaryRead, renameFailure, renameFile } = useExamWorkspaceRename({
    isBusy: () => isBusy.value,
    operationBusy,
    summary,
    savedDocuments,
    teacher: store.teacher,
  });

  const { retryItem: requestItemRetry } = useExamWorkspaceItemRetry({
    isBusy: () => isBusy.value,
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
    const before = prior?.items.find((item) => item.item_id === itemId);
    await requestItemRetry(itemId, kind);
    const after = workspaceDocument.value?.items.find((item) => item.item_id === itemId);
    if (after !== before) {
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
  });

  const { saveDocumentAs } = useExamWorkspaceSave({
    applyResponse,
    arrivals,
    beginDocumentRead,
    isBusy,
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
  const fieldCommands = useExamWorkspaceDocumentFields({ editDocument });

  /**
   * A store or a position move confirmed this document; the exam file holds
   * it now. The saved baseline becomes the confirmed snapshot, and the open
   * copy's revision follows the file: the working copy keeps its content
   * (later edits stay), only its revision tracks the confirmed file version,
   * so dirty still means the content differs from the file.
   */
  function noteStored(document: NativeExamDocument): void {
    savedDocument.value = document;
    const current = workspaceDocument.value;
    if (current !== null && current.revision !== document.revision) {
      workspaceDocument.value = { ...current, revision: document.revision };
    }
  }

  /** A server command (parent, change type) stored a new step; show its document. */
  function applyCommandResponse(response: ExamWorkspaceDocumentResponse): void {
    applyResponse(response);
    replacingScope.replayHeld();
  }

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
    setCourse,
    selectedItem,
    selectedItemId,
    summary,
    titleWithoutText,
    updateItemGapValues: keying.updateItemGapValues,
    removeItemAutomaticValue: keying.removeItemAutomaticValue,
    workspaceDocument,
  };
}
