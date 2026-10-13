/**
 * Exam workspace document state.
 *
 * Domain purpose:
 *   Own the teacher-facing exam workspace lifecycle: import a .docx exam,
 *   list and reopen saved documents, edit items locally with immutable
 *   updates, move advisory answer-key proposals into the editor, refuse a
 *   save the server would reject with Swedish copy naming the questions,
 *   save versioned revisions, and recover from stale-save conflicts by reloading
 *   the latest saved version.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`.
 *   - Delegates transport to `api/examWorkspace.ts`.
 *   - Applies item edits from `examWorkspaceItemEdits` through one patch path.
 *   - Checks a save against `examWorkspaceItemSaveRules` before sending it.
 *   - Reports outcomes through the shared toast store.
 */

import { computed, ref } from "vue";

import { isApiError } from "../../../api/client";
import type { ApiError } from "../../../api/client";
import {
  getExamWorkspaceDocument,
  listExamWorkspaceDocuments,
  saveExamWorkspaceDocument as requestSaveExamWorkspaceDocument,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamBodySegment,
  NativeExamDocument,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { nextItemId } from "./examWorkspaceConversionMerge";
import {
  newTeacherItem,
  reviewed,
  withChoiceText,
  withCorrectChoices,
  withGapValues,
  withMarkingGuide,
  withMatchEntryText,
  withMatchPairs,
  withParagraphSegments,
  withPoints,
  withProposal,
  withTitle,
} from "./examWorkspaceItemEdits";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";

export { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./useExamWorkspaceConversion";

export const EXAM_WORKSPACE_CONFLICT_COPY =
  "Det gick inte att spara eftersom provet ändrades någon annanstans. Den senaste sparade versionen har lästs in på nytt.";

const SAVE_SUCCESS_COPY = "Provet är sparat.";
const SAVE_FAILURE_COPY = "Det gick inte att spara provet. Försök igen.";
const RELOAD_SUCCESS_COPY = "Den senaste sparade versionen är inläst.";
const RELOAD_FAILURE_COPY = "Det gick inte att läsa in provet på nytt. Försök igen.";
const OPEN_FAILURE_COPY = "Det gick inte att öppna provet. Försök igen.";
const LIST_FAILURE_COPY = "Det gick inte att hämta dina sparade prov.";

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
 * Merge a fetched saved-document list into the entries already known locally.
 * A local entry wins when the response lacks its lineage (for example an
 * import that finished while the list request was in flight) or when it holds
 * a newer version; the response supplies everything else.
 */
export function mergeSavedDocuments(
  local: ExamWorkspaceDocumentSummary[],
  fetched: ExamWorkspaceDocumentSummary[],
): ExamWorkspaceDocumentSummary[] {
  const localByLineage = new Map(local.map((entry) => [entry.lineage_id, entry]));
  const fetchedLineages = new Set(fetched.map((entry) => entry.lineage_id));
  const localOnly = local.filter((entry) => !fetchedLineages.has(entry.lineage_id));
  const merged = fetched.map((entry) => {
    const known = localByLineage.get(entry.lineage_id);
    return known && known.version > entry.version ? known : entry;
  });
  return [...localOnly, ...merged];
}

export function useExamWorkspaceDocument() {
  const toast = useToast();

  const workspaceDocument = ref<NativeExamDocument | null>(null);
  const serverDocument = ref<NativeExamDocument | null>(null);
  const summary = ref<ExamWorkspaceDocumentSummary | null>(null);
  const notes = ref<string[]>([]);
  const isDirty = ref(false);
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
    importDocument,
    isConverting,
    isEditingConversion,
    isImporting,
    retryConversionStatus,
    syncAfterConflict,
  } = useExamWorkspaceConversion(() => isBusy.value, {
    applyResponse,
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
  // While its batches convert, the imported exam is already editable.
  const isBusy = computed(
    () =>
      operationBusy.value ||
      isImporting.value ||
      (isConverting.value && !isEditingConversion.value),
  );

  const selectedItem = computed<NativeExamItem | null>(() => {
    const current = workspaceDocument.value;
    if (!current || selectedItemId.value === null) {
      return null;
    }
    return current.items.find((item) => item.item_id === selectedItemId.value) ?? null;
  });

  function applyResponse(
    response: ExamWorkspaceDocumentResponse,
    local: NativeExamDocument = response.document,
    dirty = false,
  ): void {
    workspaceDocument.value = local;
    serverDocument.value = response.document;
    summary.value = response.summary;
    savedDocuments.value = savedDocuments.value.some(
      (entry) => entry.lineage_id === response.summary.lineage_id,
    )
      ? savedDocuments.value.map((entry) =>
          entry.lineage_id === response.summary.lineage_id ? response.summary : entry,
        )
      : [response.summary, ...savedDocuments.value];
    notes.value = response.notes;
    isDirty.value = dirty;
    adoptConversion(response);
    const items = local.items;
    selectedItemId.value = items.some((item) => item.item_id === selectedItemId.value)
      ? selectedItemId.value
      : (items[0]?.item_id ?? null);
  }

  async function loadSavedDocuments(): Promise<void> {
    try {
      const response = await listExamWorkspaceDocuments();
      savedDocuments.value = mergeSavedDocuments(savedDocuments.value, response.documents);
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
      const response = await getExamWorkspaceDocument(lineageId);
      selectedItemId.value = null;
      applyResponse(response);
      conflictNotice.value = null;
      return true;
    } catch {
      toast.failure(OPEN_FAILURE_COPY);
      return false;
    } finally {
      operationBusy.value = false;
    }
  }

  async function reloadAfterConflict(lineageId: string): Promise<void> {
    try {
      const response = await getExamWorkspaceDocument(lineageId);
      applyResponse(response);
    } catch {
      toast.failure(RELOAD_FAILURE_COPY);
    }
  }

  async function saveDocument(
    rejectedProposalItemIds: string[] = [],
    afterConversionConflict = false,
  ): Promise<boolean> {
    const current = workspaceDocument.value;
    const currentSummary = summary.value;
    if (!current || !currentSummary || (isBusy.value && !afterConversionConflict)) {
      return false;
    }
    const refusalCopy = examWorkspaceSaveRefusalCopy(current.items);
    if (refusalCopy) {
      toast.failure(refusalCopy);
      return false;
    }
    const expectedRevision = current.revision;
    const payload: NativeExamDocument = { ...current, revision: expectedRevision + 1 };
    operationBusy.value = true;
    try {
      const response = await requestSaveExamWorkspaceDocument(currentSummary.lineage_id, {
        document: payload,
        expectedRevision,
        rejectedProposalItemIds: [...rejectedProposalItemIds],
      });
      applyResponse(response);
      conflictNotice.value = null;
      toast.success(SAVE_SUCCESS_COPY);
      return true;
    } catch (error) {
      // A batch saved meanwhile: merge it and save again on top of it. Each
      // retry stands on a strictly newer revision, so batches bound the loop.
      const conflict = isApiError(error) && error.status === 409;
      const sync = conflict ? await syncAfterConflict(expectedRevision) : "unrelated";
      if (sync === "merged") {
        return await saveDocument(rejectedProposalItemIds, true);
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
        await reloadAfterConflict(currentSummary.lineage_id);
      } else {
        toast.failure(SAVE_FAILURE_COPY);
      }
      return false;
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
      const response = await getExamWorkspaceDocument(currentSummary.lineage_id);
      applyResponse(response);
      conflictNotice.value = null;
      toast.info(RELOAD_SUCCESS_COPY);
    } catch {
      toast.failure(RELOAD_FAILURE_COPY);
    } finally {
      operationBusy.value = false;
    }
  }

  function selectItem(itemId: string): void {
    selectedItemId.value = itemId;
  }

  /** The one path every item edit takes; a placeholder whose batch still converts is refused. */
  function patchItem(
    itemId: string,
    patch: (item: NativeExamItem) => NativeExamItem,
  ): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value || convertingItemIds.value.has(itemId)) {
      return;
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
      return;
    }
    workspaceDocument.value = { ...current, items };
    isDirty.value = true;
  }

  function updateItemTitle(itemId: string, title: string): void {
    patchItem(itemId, (item) => withTitle(item, title));
  }

  function updateItemMarkingGuide(itemId: string, guide: string | null): void {
    patchItem(itemId, (item) => withMarkingGuide(item, guide));
  }

  function updateItemPoints(itemId: string, points: number | null): void {
    patchItem(itemId, (item) => withPoints(item, points));
  }

  function updateItemParagraphSegments(
    itemId: string,
    paragraphIndex: number,
    segments: NativeExamBodySegment[],
  ): void {
    patchItem(itemId, (item) => withParagraphSegments(item, paragraphIndex, segments));
  }

  function updateItemChoiceText(itemId: string, choiceId: string, text: string): void {
    patchItem(itemId, (item) => withChoiceText(item, choiceId, text));
  }

  function updateItemCorrectChoices(itemId: string, correctChoiceIds: string[]): void {
    patchItem(itemId, (item) => withCorrectChoices(item, correctChoiceIds));
  }

  function updateItemMatchEntryText(
    itemId: string,
    side: "left" | "right",
    entryId: string,
    text: string,
  ): void {
    patchItem(itemId, (item) => withMatchEntryText(item, side, entryId, text));
  }

  function updateItemMatchPairs(itemId: string, pairs: NativeExamMatchPair[]): void {
    patchItem(itemId, (item) => withMatchPairs(item, pairs));
  }

  function updateItemGapValues(itemId: string, gapId: string, acceptedValues: string[]): void {
    patchItem(itemId, (item) => withGapValues(item, gapId, acceptedValues));
  }

  function markItemReviewed(itemId: string): void {
    patchItem(itemId, reviewed);
  }

  function applyProposal(itemId: string, proposedItem: NativeExamItem, approve: boolean): void {
    patchItem(itemId, (item) => withProposal(item, proposedItem, approve));
  }

  function addItem(): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value) {
      return;
    }
    const itemId = nextItemId(current.items.map((item) => item.item_id));
    const newItem = newTeacherItem(itemId, current.items.length + 1);
    workspaceDocument.value = { ...current, items: [...current.items, newItem] };
    selectedItemId.value = itemId;
    isDirty.value = true;
  }

  return {
    addItem,
    applyProposal,
    conflictNotice,
    conversionError,
    conversionMessage,
    conversionProgress,
    conversionStatus,
    convertingItemIds,
    isConverting,
    retryConversionStatus,
    importDocument,
    isBusy,
    isDirty,
    loadSavedDocuments,
    markItemReviewed,
    notes,
    openDocument,
    reloadDocument,
    saveDocument,
    savedDocuments,
    selectItem,
    selectedItem,
    selectedItemId,
    summary,
    updateItemParagraphSegments,
    updateItemChoiceText,
    updateItemCorrectChoices,
    updateItemGapValues,
    updateItemMarkingGuide,
    updateItemMatchEntryText,
    updateItemMatchPairs,
    updateItemPoints,
    updateItemTitle,
    workspaceDocument,
  };
}
