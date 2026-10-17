/**
 * Exam workspace document state.
 *
 * Domain purpose:
 *   Own the open exam: import, list and reopen exams, edit the working copy
 *   with immutable updates, refuse a Spara the server would reject with
 *   Swedish copy naming the questions, overwrite the exam file with Spara,
 *   recover from stale-save conflicts, and reconvert one question.
 *
 * Relationships:
 *   - Transport through `api/examWorkspace.ts`; item edits through one patch
 *     path (`useExamWorkspaceItemEdits`, `useExamWorkspaceGapKeying`).
 *   - Reports each teacher edit through `onEdit`, which the undo history
 *     (`useExamWorkspaceHistory`) turns into autosaved steps; installs the
 *     history's steps and the server commands' results.
 *   - AI suggestion arrivals, conversion merges and one-question retries
 *     through their own composables.
 *   - Dirty state: the copy differs from the saved exam file (`sameDocument`).
 */

import { computed, ref, shallowRef } from "vue";

import { isApiError } from "../../../api/client";
import type { ApiError } from "../../../api/client";
import {
  copyExamWorkspaceDocument,
  getExamWorkspaceDocument,
  listExamWorkspaceDocuments,
  saveExamWorkspaceDocument as requestSaveExamWorkspaceDocument,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  ExamCourseChoice,
  ExamListOrdering,
  NativeExamDocument,
  NativeExamHeader,
  NativeExamItem,
  NativeExamItemKind,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { examWorkspaceAssetUrls } from "./examWorkspaceAssetUrls";
import { sameDocument } from "./examWorkspaceConversionMerge";
import { useExamWorkspaceItemEdits } from "./useExamWorkspaceItemEdits";
import { withRestoredSuggestion } from "./examWorkspaceSuggestionEdits";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { mergeSavedDocuments } from "./examWorkspaceSavedDocuments";
import { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";
import { useExamWorkspaceGapKeying } from "./useExamWorkspaceGapKeying";
import { useExamWorkspaceItemRetry } from "./useExamWorkspaceItemRetry";
import { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";
import { useExamWorkspaceRename } from "./useExamWorkspaceRename";

export { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./useExamWorkspaceConversion";

export const EXAM_WORKSPACE_CONFLICT_COPY =
  "Det gick inte att spara eftersom provet ändrades någon annanstans. Den senaste sparade versionen har lästs in på nytt.";

const SAVE_FAILURE_COPY = "Det gick inte att spara provet. Försök igen.";
const RELOAD_FAILURE_COPY = "Det gick inte att läsa in provet på nytt. Försök igen.";
const OPEN_FAILURE_COPY = "Det gick inte att öppna provet. Försök igen.";
const LIST_FAILURE_COPY = "Det gick inte att hämta dina sparade prov.";
const SAVE_AS_FAILURE_COPY = "Det gick inte att spara en kopia av provet. Försök igen.";

export type ExamWorkspaceSaveAsOutcome = "saved" | "name_taken" | "failed";

function nameInUse(error: unknown): boolean {
  return (
    isApiError(error) &&
    error.status === 422 &&
    typeof error.details === "object" &&
    error.details !== null &&
    (error.details as { code?: unknown }).code === "vault_name_in_use"
  );
}

/** A save refused because it changed questions that still convert (D30). */
function refusedPlaceholderChange(error: unknown): error is ApiError {
  return (
    isApiError(error) &&
    error.status === 422 &&
    typeof error.details === "object" &&
    error.details !== null &&
    "item_ids" in error.details
  );
}

/**
 * One opening of an exam: created when a document of another lineage is
 * installed, kept while revisions of the same lineage replace the copy.
 * Compared by identity, so reopening an exam later is a new opening.
 */
export type ExamWorkspaceOpening = { readonly lineageId: string };

export type ExamWorkspaceDocumentOptions = {
  /** A teacher edit changed the copy; structural edits become an undo step at once. */
  onEdit?: (structural: boolean) => void;
  /** An undo, redo or server command is about to replace the copy; editing waits for it. */
  isReplacing?: () => boolean;
};

export function useExamWorkspaceDocument(options: ExamWorkspaceDocumentOptions = {}) {
  const toast = useToast();
  const noteEdit = options.onEdit ?? (() => undefined);
  const isReplacing = options.isReplacing ?? (() => false);

  const workspaceDocument = ref<NativeExamDocument | null>(null);
  // The last working response remains the conversion merge base, not the Spara baseline.
  const serverDocument = ref<NativeExamDocument | null>(null);
  const savedDocument = ref<NativeExamDocument | null>(null);
  const summary = ref<ExamWorkspaceDocumentSummary | null>(null);
  /** The server's newest undo step; history commands are guarded by it. */
  const historyCursor = ref<string | null>(null);
  const listOrdering = ref<ExamListOrdering>("course");
  const notes = ref<string[]>([]);
  const openExam = shallowRef<ExamWorkspaceOpening | null>(null);
  const isDirty = computed(() => !sameDocument(workspaceDocument.value, savedDocument.value));
  /** The saved version the open copy stands on. */
  const savedRevision = computed(() => savedDocument.value?.revision ?? null);
  const operationBusy = ref(false);
  const conflictNotice = ref<string | null>(null);
  const selectedItemId = ref<string | null>(null);
  const savedDocuments = ref<ExamWorkspaceDocumentSummary[]>([]);
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
  } = useExamWorkspaceConversion(() => isBusy.value, {
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
  });
  const arrivals = useExamWorkspaceSaveArrivals({ convertingItemIds, isOpen, workspaceDocument });
  const { applyArrivingSuggestions } = arrivals;
  // While its batches convert, the imported exam is already editable.
  const isOperationBusy = computed(
    () =>
      operationBusy.value ||
      isImporting.value ||
      (isConverting.value && !isEditingConversion.value),
  );
  /** No edit, save or reload may start: an operation runs or the copy is about to be replaced. */
  const isBusy = computed(() => isOperationBusy.value || isReplacing());

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
    serverDocument.value = response.document;
    savedDocument.value = response.saved_document;
    summary.value = response.summary;
    historyCursor.value = response.history_cursor;
    savedDocuments.value = savedDocuments.value.some(
      (entry) => entry.lineage_id === response.summary.lineage_id,
    )
      ? savedDocuments.value.map((entry) =>
          entry.lineage_id === response.summary.lineage_id ? response.summary : entry,
        )
      : [response.summary, ...savedDocuments.value];
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

  async function loadSavedDocuments(): Promise<void> {
    const reconcile = beginSummaryRead();
    try {
      const response = await listExamWorkspaceDocuments();
      savedDocuments.value = mergeSavedDocuments(savedDocuments.value, response.documents.map(reconcile));
      listOrdering.value = response.ordering;
    } catch {
      toast.failure(LIST_FAILURE_COPY);
    }
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

  /** Returns whether the reloaded revision replaced the teacher's copy. */
  async function reloadAfterConflict(lineageId: string): Promise<boolean> {
    try {
      const reconcile = beginDocumentRead();
      const response = reconcile(await getExamWorkspaceDocument(lineageId));
      applyResponse(response);
      keying.invalidateCopy();
      return true;
    } catch {
      toast.failure(RELOAD_FAILURE_COPY);
      return false;
    }
  }

  async function saveDocument(afterConversionConflict = false): Promise<boolean> {
    const current = workspaceDocument.value;
    const currentSummary = summary.value;
    if (!current || !currentSummary || (isBusy.value && !afterConversionConflict)) {
      return false;
    }
    if (!current.title.trim()) {
      toast.failure("Skriv en titel innan du sparar provet.");
      return false;
    }
    const refusalCopy = examWorkspaceSaveRefusalCopy(current.items);
    if (refusalCopy) {
      toast.failure(refusalCopy);
      return false;
    }
    const expectedRevision = current.revision;
    const payload: NativeExamDocument = { ...current, revision: expectedRevision + 1 };
    const payloadMark = arrivals.payloadMark();
    const openedArrivals = arrivals.beginSave();
    const keyingMark = keying.payloadMark();
    const openedKeying = keying.beginSave();
    operationBusy.value = true;
    try {
      const response = await requestSaveExamWorkspaceDocument(currentSummary.lineage_id, {
        document: payload,
        expectedRevision,
      });
      applyResponse(response);
      // The response holds the payload; arrivals that landed after it was read run again on it.
      arrivals.replayAfterResponse(payloadMark);
      // The response holds the payload; spellings merged in after it was read run again on it.
      keying.replayAfterResponse(keyingMark);
      // "Sparat HH:MM" in the header is the success state; toasts report failures only.
      conflictNotice.value = null;
      return true;
    } catch (error) {
      // A batch saved meanwhile: merge it and save again on top of it. Each
      // retry stands on a strictly newer revision, so batches bound the loop.
      const conflict = isApiError(error) && error.status === 409;
      const sync = conflict ? await syncAfterConflict(expectedRevision) : "unrelated";
      if (sync === "merged") {
        return await saveDocument(true);
      }
      if (refusedPlaceholderChange(error)) {
        // The server names the converting questions the save changed; the copy stays.
        toast.failure(error.message);
      } else if (sync === "unknown") {
        // Reloading would replace the teacher's copy with a revision never merged into it.
        toast.failure(SAVE_FAILURE_COPY);
      } else if (conflict) {
        conflictNotice.value = EXAM_WORKSPACE_CONFLICT_COPY;
        toast.failure(EXAM_WORKSPACE_CONFLICT_COPY);
        if (await reloadAfterConflict(currentSummary.lineage_id)) {
          // The reloaded head never held them: arrivals since the save began run again on it.
          arrivals.replayAfterReload();
        }
      } else {
        toast.failure(SAVE_FAILURE_COPY);
      }
      // Every other failure left the teacher's copy, and each arrival's single effect, in place.
      return false;
    } finally {
      arrivals.endSave(openedArrivals);
      keying.endSave(openedKeying);
      operationBusy.value = false;
    }
  }

  /**
   * Spara som: the working copy becomes a new exam named `name` with its own
   * history, and opens in place; the exam it came from keeps its last save.
   */
  async function saveDocumentAs(name: string): Promise<ExamWorkspaceSaveAsOutcome> {
    const current = workspaceDocument.value;
    const currentSummary = summary.value;
    if (!current || !currentSummary || isBusy.value) {
      return "failed";
    }
    if (!current.title.trim()) {
      toast.failure("Skriv en titel innan du sparar provet.");
      return "failed";
    }
    operationBusy.value = true;
    try {
      const response = await copyExamWorkspaceDocument(currentSummary.lineage_id, name, current);
      applyResponse(response);
      keying.invalidateCopy();
      conflictNotice.value = null;
      return "saved";
    } catch (error) {
      if (nameInUse(error)) {
        return "name_taken";
      }
      toast.failure(SAVE_AS_FAILURE_COPY);
      return "failed";
    } finally {
      operationBusy.value = false;
    }
  }

  async function reloadDocument(): Promise<void> {
    const currentSummary = summary.value;
    if (!currentSummary || isBusy.value) {
      return;
    }
    operationBusy.value = true;
    try {
      const reconcile = beginDocumentRead();
      const response = reconcile(await getExamWorkspaceDocument(currentSummary.lineage_id));
      applyResponse(response);
      keying.invalidateCopy();
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
    noteEdit(false);
  }

  function setCourse(course: ExamCourseChoice | null): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value) return;
    workspaceDocument.value = { ...current, header: { ...current.header, course } };
    noteEdit(true);
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
    const before = workspaceDocument.value?.items.find((item) => item.item_id === itemId);
    await requestItemRetry(itemId, kind);
    const after = workspaceDocument.value?.items.find((item) => item.item_id === itemId);
    if (after !== before) {
      keying.invalidateItem(itemId);
      noteEdit(true);
    }
  }

  /** The one path every item edit takes; a placeholder whose batch still converts is refused. */
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
    workspaceDocument.value = { ...current, items };
    noteEdit(structural);
    return true;
  }

  // Every gap keying edit and its asynchronous misspelling reply.
  const keying = useExamWorkspaceGapKeying({ openExam, patchItem, workspaceDocument });

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
    workspaceDocument.value = edit(current);
    if (selectId !== null) {
      selectedItemId.value = selectId;
    }
    noteEdit(structural);
    return true;
  }

  /** The instruction text above an instruction's deluppgifter, typed like a question's text. */
  function setParentInstruction(parentId: string, instruction: NativeExamParent["instruction"]): void {
    editDocument(
      (document) => ({
        ...document,
        parents: document.parents.map((parent) =>
          parent.parent_id === parentId ? { ...parent, instruction } : parent,
        ),
      }),
      null,
      false,
    );
  }

  /** The exam's Centralt innehåll ticks; each tick is its own undo step. */
  function setTags(tags: NativeExamHeader["tags"]): void {
    editDocument((document) => ({ ...document, header: { ...document.header, tags } }));
  }

  function keepSelection(document: NativeExamDocument): void {
    if (!document.items.some((item) => item.item_id === selectedItemId.value)) {
      selectedItemId.value = document.items[0]?.item_id ?? null;
    }
  }

  /** Put an undo step's document in front of the teacher; not an edit. */
  function installDocument(document: NativeExamDocument): void {
    workspaceDocument.value = document;
    keying.invalidateCopy();
    keepSelection(document);
  }

  /** A server command (parent, change type) stored a new step; show its document. */
  function applyCommandResponse(response: ExamWorkspaceDocumentResponse): void {
    applyResponse(response);
    keying.invalidateCopy();
  }

  return {
    ...itemEdits,
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
    isOpen,
    loadSavedDocuments,
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
    setParentInstruction,
    setTags,
    selectedItem,
    selectedItemId,
    summary,
    updateItemGapValues: keying.updateItemGapValues,
    removeItemAutomaticValue: keying.removeItemAutomaticValue,
    workspaceDocument,
  };
}
