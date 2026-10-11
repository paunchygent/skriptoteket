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
 *   - Checks a save against `examWorkspaceItemSaveRules` before sending it.
 *   - Reports outcomes through the shared toast store.
 */

import { computed, ref } from "vue";

import { isApiError } from "../../../api/client";
import {
  getExamWorkspaceDocument,
  listExamWorkspaceDocuments,
  saveExamWorkspaceDocument as requestSaveExamWorkspaceDocument,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamAnswerKeyOrigin,
  NativeExamBodySegment,
  NativeExamDocument,
  NativeExamItem,
  NativeExamMatchPair,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";
import { nextItemId } from "./examWorkspaceConversionMerge";
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

/** A teacher edit keys the item only while it still carries key data. */
function teacherKeyOrigin(hasKeyData: boolean): NativeExamAnswerKeyOrigin {
  return hasKeyData ? "teacher_authored" : "absent";
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
      // A batch saved meanwhile: merge it and save once more on top of it.
      if (
        isApiError(error) &&
        error.status === 409 &&
        !afterConversionConflict &&
        (await syncAfterConflict(expectedRevision))
      ) {
        return await saveDocument(rejectedProposalItemIds, true);
      }
      if (isApiError(error) && error.status === 409) {
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

  function patchItem(
    itemId: string,
    patch: (item: NativeExamItem) => NativeExamItem,
  ): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value) {
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
    patchItem(itemId, (item) => ({
      ...item,
      title: title.trim().length > 0 ? title : null,
    }));
  }

  function updateItemMarkingGuide(itemId: string, guide: string | null): void {
    patchItem(itemId, (item) => ({ ...item, marking_guide: guide }));
  }

  function updateItemPoints(itemId: string, points: number | null): void {
    patchItem(itemId, (item) => ({ ...item, points }));
  }

  /** Replace one paragraph's segments, as serialized by the inline body editor. */
  function updateItemParagraphSegments(
    itemId: string,
    paragraphIndex: number,
    segments: NativeExamBodySegment[],
  ): void {
    patchItem(itemId, (item) => ({
      ...item,
      body: item.body.map((paragraph, candidateParagraphIndex) =>
        candidateParagraphIndex === paragraphIndex ? { segments } : paragraph,
      ),
    }));
  }

  function updateItemChoiceText(itemId: string, choiceId: string, text: string): void {
    patchItem(itemId, (item) => ({
      ...item,
      choices: item.choices.map((choice) =>
        choice.choice_id === choiceId ? { ...choice, text } : choice,
      ),
    }));
  }

  function updateItemCorrectChoices(itemId: string, correctChoiceIds: string[]): void {
    patchItem(itemId, (item) => ({
      ...item,
      answer_key: {
        ...item.answer_key,
        correct_choice_ids: correctChoiceIds,
        origin: teacherKeyOrigin(correctChoiceIds.length > 0),
      },
    }));
  }

  function updateItemMatchEntryText(
    itemId: string,
    side: "left" | "right",
    entryId: string,
    text: string,
  ): void {
    patchItem(itemId, (item) =>
      side === "left"
        ? {
            ...item,
            match_left: item.match_left.map((entry) =>
              entry.left_id === entryId ? { ...entry, text } : entry,
            ),
          }
        : {
            ...item,
            match_right: item.match_right.map((entry) =>
              entry.right_id === entryId ? { ...entry, text } : entry,
            ),
          },
    );
  }

  function updateItemMatchPairs(itemId: string, pairs: NativeExamMatchPair[]): void {
    patchItem(itemId, (item) => ({
      ...item,
      answer_key: {
        ...item.answer_key,
        match_pairs: pairs,
        origin: teacherKeyOrigin(pairs.length > 0),
      },
    }));
  }

  function updateItemGapValues(
    itemId: string,
    gapId: string,
    acceptedValues: string[],
  ): void {
    patchItem(itemId, (item) => {
      const gaps = item.gaps.map((gap) =>
        gap.gap_id === gapId ? { ...gap, accepted_values: acceptedValues } : gap,
      );
      const hasKeyData = gaps.some((gap) => gap.accepted_values.length > 0);
      return {
        ...item,
        answer_key: { ...item.answer_key, origin: teacherKeyOrigin(hasKeyData) },
        gaps,
      };
    });
  }

  function markItemReviewed(itemId: string): void {
    patchItem(itemId, (item) => ({
      ...item,
      answer_key:
        item.answer_key.origin === "machine_proposed"
          ? { ...item.answer_key, origin: "reviewed_advisory" }
          : item.answer_key,
      review: { ...item.review, state: "review_complete" },
    }));
  }

  /**
   * Move an advisory proposal into the editor as an unreviewed prefill
   * (`machine_proposed`, item marked `review_required`). With `approve`, the
   * teacher accepts the key unchanged in the same step, which records it as
   * `reviewed_advisory` and leaves the item's review state and reasons as
   * they were: parse-confidence review still needs the explicit
   * "mark reviewed" action.
   */
  function applyProposal(itemId: string, proposedItem: NativeExamItem, approve: boolean): void {
    patchItem(itemId, (item) => {
      const gaps = item.gaps.map((gap) => {
        const proposedGap = proposedItem.gaps.find(
          (candidate) => candidate.gap_id === gap.gap_id,
        );
        return proposedGap ? { ...gap, accepted_values: proposedGap.accepted_values } : gap;
      });
      if (approve) {
        return {
          ...item,
          answer_key: { ...proposedItem.answer_key, origin: "reviewed_advisory" },
          gaps,
        };
      }
      return {
        ...item,
        answer_key: { ...proposedItem.answer_key, origin: "machine_proposed" },
        gaps,
        review: { ...item.review, state: "review_required" },
      };
    });
  }

  function addItem(): void {
    const current = workspaceDocument.value;
    if (!current || isBusy.value) {
      return;
    }
    const itemId = nextItemId(current.items.map((item) => item.item_id));
    const newItem: NativeExamItem = {
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
      body: [{ segments: [{ kind: "text", text: "Ny fråga" }] }],
      choices: [],
      gaps: [],
      item_id: itemId,
      kind: "free_text",
      match_left: [],
      match_right: [],
      points: null,
      review: {
        confidence: null,
        parse_origin: "teacher_created",
        reasons: [],
        state: "review_complete",
      },
      sequence: current.items.length + 1,
      source_anchor: null,
      title: null,
    };
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
