/**
 * Exam workspace document state.
 *
 * Domain purpose:
 *   Own the teacher-facing exam workspace lifecycle: import a .docx exam,
 *   list and reopen saved documents, edit items locally with immutable
 *   updates, refuse a save the server would reject with Swedish copy naming
 *   the questions,
 *   save versioned revisions, recover from stale-save conflicts by reloading
 *   the latest saved version, and reconvert one review question from its
 *   stored source with a type the teacher keeps or changes.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`.
 *   - Delegates transport to `api/examWorkspace.ts`.
 *   - Applies item edits from `examWorkspaceItemEdits` through one patch path.
 *   - Checks a save against `examWorkspaceItemSaveRules` before sending it.
 *   - Writes arriving AI suggestions and keeps their single effect across
 *     saves through `useExamWorkspaceSaveArrivals`, only into the exam
 *     opening that requested them.
 *   - Dirty state is derived: the copy differs from the last server document
 *     (`sameDocument`).
 *   - Reports outcomes through the shared toast store.
 */

import { computed, ref, shallowRef } from "vue";

import { isApiError } from "../../../api/client";
import type { ApiError } from "../../../api/client";
import {
  examWorkspaceAssetUrl,
  getExamWorkspaceDocument,
  listExamWorkspaceDocuments,
  retryExamWorkspaceItem,
  saveExamWorkspaceDocument as requestSaveExamWorkspaceDocument,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamBodySegment,
  NativeExamDocument,
  NativeExamItem,
  NativeExamItemKind,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { nextItemId, sameDocument, sameValue } from "./examWorkspaceConversionMerge";
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
  withRestoredSuggestion,
} from "./examWorkspaceItemEdits";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { useExamWorkspaceConversion } from "./useExamWorkspaceConversion";
import { useExamWorkspaceSaveArrivals } from "./useExamWorkspaceSaveArrivals";

export { EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./useExamWorkspaceConversion";

export const EXAM_WORKSPACE_CONFLICT_COPY =
  "Det gick inte att spara eftersom provet ändrades någon annanstans. Den senaste sparade versionen har lästs in på nytt.";

const RETRY_FAILURE_COPY = "Det gick inte att konvertera om frågan. Försök igen.";
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

/**
 * One opening of an exam: created when a document of another lineage is
 * installed, kept while revisions of the same lineage replace the copy.
 * Compared by identity, so reopening an exam later is a new opening.
 */
export type ExamWorkspaceOpening = { readonly lineageId: string };

export function useExamWorkspaceDocument() {
  const toast = useToast();

  const workspaceDocument = ref<NativeExamDocument | null>(null);
  const serverDocument = ref<NativeExamDocument | null>(null);
  const summary = ref<ExamWorkspaceDocumentSummary | null>(null);
  const notes = ref<string[]>([]);
  const openExam = shallowRef<ExamWorkspaceOpening | null>(null);
  const isDirty = computed(() => !sameDocument(workspaceDocument.value, serverDocument.value));
  /** The saved version the open copy stands on. */
  const savedRevision = computed(() => serverDocument.value?.revision ?? null);
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

  /** The open document's pictures by asset id, for the editor's image atoms. */
  const assetUrls = computed<Record<string, string>>(() => {
    const current = workspaceDocument.value;
    const lineageId = summary.value?.lineage_id;
    if (!current || !lineageId || current.assets.length === 0) {
      return {};
    }
    return Object.fromEntries(
      current.assets.map((asset) => [
        asset.asset_id,
        examWorkspaceAssetUrl(lineageId, asset.asset_id, current.revision),
      ]),
    );
  });

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
    summary.value = response.summary;
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

  /** Returns whether the reloaded revision replaced the teacher's copy. */
  async function reloadAfterConflict(lineageId: string): Promise<boolean> {
    try {
      const response = await getExamWorkspaceDocument(lineageId);
      applyResponse(response);
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
    const refusalCopy = examWorkspaceSaveRefusalCopy(current.items);
    if (refusalCopy) {
      toast.failure(refusalCopy);
      return false;
    }
    const expectedRevision = current.revision;
    const payload: NativeExamDocument = { ...current, revision: expectedRevision + 1 };
    const payloadMark = arrivals.payloadMark();
    const openedArrivals = arrivals.beginSave();
    operationBusy.value = true;
    try {
      const response = await requestSaveExamWorkspaceDocument(currentSummary.lineage_id, {
        document: payload,
        expectedRevision,
      });
      applyResponse(response);
      // The response holds the payload; arrivals that landed after it was read run again on it.
      arrivals.replayAfterResponse(payloadMark);
      conflictNotice.value = null;
      toast.success(SAVE_SUCCESS_COPY);
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

  /**
   * The opening, lineage and saved revision a retry request was sent for are
   * still the ones in front of the teacher.
   */
  function retryRequestIsLive(
    opening: ExamWorkspaceOpening,
    lineageId: string,
    revision: number,
  ): boolean {
    return (
      openExam.value === opening &&
      summary.value?.lineage_id === lineageId &&
      workspaceDocument.value?.revision === revision &&
      serverDocument.value?.revision === revision
    );
  }

  /**
   * Reconvert one review question from the saved revision's stored source
   * with the teacher's chosen type (TASK-SKRIPT-39-05-09 D1). The reply
   * replaces only that draft item, and only while the same opening still
   * stands on the same revision with that item unedited; a reply that lost
   * its place, or a failure of a request that did, changes nothing.
   */
  async function retryItem(itemId: string, kind: NativeExamItemKind): Promise<void> {
    const current = workspaceDocument.value;
    const currentSummary = summary.value;
    const opening = openExam.value;
    if (!current || !currentSummary || !opening || isBusy.value) {
      return;
    }
    const target = current.items.find((item) => item.item_id === itemId) ?? null;
    if (
      target === null ||
      target.retry_source === null ||
      target.review.state !== "review_required"
    ) {
      return;
    }
    const lineageId = currentSummary.lineage_id;
    const revision = current.revision;
    operationBusy.value = true;
    try {
      const response = await retryExamWorkspaceItem(lineageId, current, itemId, kind);
      const draft = workspaceDocument.value;
      const draftTarget = draft?.items.find((item) => item.item_id === itemId) ?? null;
      if (
        draft === null ||
        response.lineage_id !== lineageId ||
        !retryRequestIsLive(opening, lineageId, revision) ||
        draftTarget === null ||
        !sameValue(draftTarget, target)
      ) {
        return;
      }
      workspaceDocument.value = {
        ...draft,
        items: draft.items.map((item) => (item.item_id === itemId ? response.item : item)),
      };
    } catch (error) {
      if (!retryRequestIsLive(opening, lineageId, revision)) {
        return;
      }
      const serverCopy =
        isApiError(error) && error.code !== "HTTP_ERROR" && error.message !== "Validation error"
          ? error.message
          : null;
      toast.failure(serverCopy || RETRY_FAILURE_COPY);
    } finally {
      operationBusy.value = false;
    }
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

  function restoreItemSuggestion(itemId: string): void {
    patchItem(itemId, (item) => withRestoredSuggestion(item));
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
  }

  return {
    addItem,
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
    isOpen,
    loadSavedDocuments,
    markItemReviewed,
    notes,
    openDocument,
    openExam: computed(() => openExam.value),
    reloadDocument,
    restoreItemSuggestion,
    retryItem,
    saveDocument,
    savedDocuments,
    savedRevision,
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
    workspaceDocument,
  };
}
