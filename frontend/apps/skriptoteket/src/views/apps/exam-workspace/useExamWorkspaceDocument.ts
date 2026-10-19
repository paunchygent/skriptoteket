/**
 * Exam workspace document state.
 *
 * Domain purpose:
 *   Own the open exam: import and reopen exams, edit the working copy with
 *   immutable updates, track dirty and busy state, select a question, and
 *   reconvert one question.
 *
 * Relationships:
 *   - Transport through `api/examWorkspace.ts`; item edits through one patch
 *     path (`useExamWorkspaceItemEdits`, `useExamWorkspaceGapKeying`).
 *   - Reports each teacher edit through `onEdit`, which the undo history
 *     (`useExamWorkspaceHistory`) turns into autosaved steps; installs the
 *     history's steps and the server commands' results.
 *   - The whole-document field commands (exam and part instructions, tags,
 *     printed-total accepts) in `useExamWorkspaceDocumentFields`, built on
 *     `editDocument` here.
 *   - Spara, Spara som and stale-save recovery (`useExamWorkspaceSave`), the
 *     saved-exams list (`useExamWorkspaceSavedList`), AI suggestion arrivals,
 *     conversion merges and one-question retries through their own composables.
 *   - Dirty state: the copy differs from the saved exam file (`sameDocument`).
 */

import { computed, ref, shallowRef } from "vue";

import { getExamWorkspaceDocument } from "../../../api/examWorkspace";
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
import { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";
import { useExamWorkspaceDocumentFields } from "./useExamWorkspaceDocumentFields";
import { useExamWorkspaceGapKeying } from "./useExamWorkspaceGapKeying";
import { useExamWorkspaceItemRetry } from "./useExamWorkspaceItemRetry";
import { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";
import { useExamWorkspaceRename } from "./useExamWorkspaceRename";
import { RELOAD_FAILURE_COPY, useExamWorkspaceSave } from "./useExamWorkspaceSave";
import { useExamWorkspaceSavedList } from "./useExamWorkspaceSavedList";
import { useExamWorkspaceTitleVerdict } from "./useExamWorkspaceTitleVerdict";

export { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./useExamWorkspaceConversion";

export { EXAM_WORKSPACE_CONFLICT_COPY } from "./useExamWorkspaceSave";
export type { ExamWorkspaceSaveAsOutcome } from "./useExamWorkspaceSave";

const OPEN_FAILURE_COPY = "Det gick inte att öppna provet. Försök igen.";

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
};

export function useExamWorkspaceDocument(options: ExamWorkspaceDocumentOptions = {}) {
  const toast = useToast();
  const noteEdit = options.onEdit ?? (() => undefined);

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
    useExamWorkspaceSavedList({ beginSummaryRead: () => beginSummaryRead() });
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
        conflictNotice.value = null;
      },
      isDirty,
      isSaving: () => operationBusy.value,
      serverDocument,
      summary,
      workspaceDocument,
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
  /** The arrival marks a replacing read was started at; null while none runs. */
  let held: { arrivals: number; keying: number } | null = null;
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
    examWorkspaceAssetUrls(workspaceDocument.value, summary.value?.lineage_id ?? null),
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
      const response = reconcile(await getExamWorkspaceDocument(lineageId));
      selectedItemId.value = null;
      applyResponse(response);
      keying.invalidateCopy();
      conflictNotice.value = null;
      return true;
    } catch {
      toast.failure(OPEN_FAILURE_COPY);
      return false;
    } finally {
      operationBusy.value = false;
    }
  }

  /**
   * Read the exam again. Also the conflict recovery of undo and the server
   * commands, so only a running operation holds it back, not their own lock.
   */
  async function reloadDocument(): Promise<void> {
    const currentSummary = summary.value;
    if (!currentSummary || isOperationBusy.value) {
      return;
    }
    operationBusy.value = true;
    try {
      const reconcile = beginDocumentRead();
      const response = reconcile(await getExamWorkspaceDocument(currentSummary.lineage_id));
      applyResponse(response);
      keying.invalidateCopy();
      if (held) {
        // A conflict inside a replacing read: its suggestions run again on the reloaded exam.
        arrivals.replayAfterResponse(held.arrivals);
      }
      conflictNotice.value = null;
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
    if (!current || isBusy.value) return;
    workspaceDocument.value = { ...current, title };
    noteEdit(false, current);
  }

  function setCourse(course: ExamCourseChoice | null): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value) return;
    workspaceDocument.value = { ...current, header: { ...current.header, course } };
    noteEdit(true, current);
  }

  const { beginSummaryRead, renameFailure, renameFile } = useExamWorkspaceRename({
    isBusy: () => isBusy.value,
    operationBusy,
    summary,
    savedDocuments,
  });

  const { retryItem: requestItemRetry } = useExamWorkspaceItemRetry({
    isBusy: () => isBusy.value,
    openExam,
    operationBusy,
    serverDocument,
    summary,
    workspaceDocument,
  });

  /** Retry one question, and drop in-flight keying replies for the item it replaced. */
  async function retryItem(itemId: string, kind: NativeExamItemKind): Promise<void> {
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
    if (!current || isBusy.value || convertingItemIds.value.has(itemId)) {
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
  const keying = useExamWorkspaceGapKeying({ openExam, patchItem, workspaceDocument });

  const { conflictNotice, saveDocument, saveDocumentAs } = useExamWorkspaceSave({
    applyResponse,
    arrivals,
    beginDocumentRead,
    isBusy,
    keying,
    operationBusy,
    summary,
    syncAfterConflict,
    workspaceDocument,
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
    if (!current || isBusy.value) {
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

  function keepSelection(document: NativeExamDocument): void {
    if (!document.items.some((item) => item.item_id === selectedItemId.value)) {
      selectedItemId.value = document.items[0]?.item_id ?? null;
    }
  }

  /**
   * Run an undo, redo or server command that replaces the copy. Editing is
   * locked meanwhile, and AI suggestions and spelling replies that arrive
   * during its read run again on the document it installs, so a delivered
   * result is never overwritten. Replies whose question or gap the document
   * no longer holds do not apply, as everywhere else.
   */
  async function replaceCopy<T>(run: () => Promise<T>): Promise<T> {
    replacing.value = true;
    const marks = { arrivals: arrivals.payloadMark(), keying: keying.payloadMark() };
    const openedArrivals = arrivals.beginHold();
    const openedKeying = keying.beginHold();
    held = marks;
    try {
      return await run();
    } finally {
      held = null;
      arrivals.endHold(openedArrivals);
      keying.endHold(openedKeying);
      replacing.value = false;
    }
  }

  function replayHeld(): void {
    if (held) {
      arrivals.replayAfterResponse(held.arrivals);
      keying.replayAfterResponse(held.keying);
    }
  }

  /** Put an undo step's document in front of the teacher; not an edit. */
  function installDocument(document: NativeExamDocument): void {
    workspaceDocument.value = document;
    keepSelection(document);
    replayHeld();
  }

  /** A server command (parent, change type) stored a new step; show its document. */
  function applyCommandResponse(response: ExamWorkspaceDocumentResponse): void {
    applyResponse(response);
    replayHeld();
  }

  return {
    ...itemEdits,
    ...fieldCommands,
    applyCommandResponse,
    editDocument,
    historyCursor,
    installDocument,
    listOrdering,
    applyArrivingSuggestions,
    assetUrls,
    conflictNotice,
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
    replaceCopy,
    isOpen,
    loadSavedDocuments,
    noteExportBlockers,
    notes,
    openDocument,
    openExam: computed(() => openExam.value),
    reloadDocument,
    renameFailure,
    renameFile,
    restoreItemSuggestion,
    retryItem,
    saveDocument,
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
