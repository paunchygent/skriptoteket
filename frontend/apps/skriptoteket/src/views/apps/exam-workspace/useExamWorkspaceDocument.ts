/**
 * Exam workspace document state.
 *
 * Domain purpose:
 *   Own the teacher-facing exam workspace lifecycle: import a .docx exam,
 *   edit items locally with immutable updates, save versioned revisions, and
 *   recover from stale-save conflicts by reloading the latest saved version.
 *
 * Relationships:
 *   - Used by `ExamWorkspaceView`.
 *   - Delegates transport to `api/examWorkspace.ts`.
 *   - Reports outcomes through the shared toast store.
 */

import { computed, ref } from "vue";

import { isApiError } from "../../../api/client";
import {
  getExamWorkspaceDocument,
  importExamWorkspaceDocument as requestImportExamWorkspaceDocument,
  saveExamWorkspaceDocument as requestSaveExamWorkspaceDocument,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceDocumentSummary,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { useToast } from "../../../composables/useToast";

export const EXAM_WORKSPACE_CONFLICT_COPY =
  "Det gick inte att spara eftersom provet ändrades någon annanstans. Den senaste sparade versionen har lästs in på nytt.";

const IMPORT_SUCCESS_COPY = "Provet är inläst.";
const IMPORT_FAILURE_COPY = "Det gick inte att läsa in provet. Försök igen.";
const SAVE_SUCCESS_COPY = "Provet är sparat.";
const SAVE_FAILURE_COPY = "Det gick inte att spara provet. Försök igen.";
const RELOAD_SUCCESS_COPY = "Den senaste sparade versionen är inläst.";
const RELOAD_FAILURE_COPY = "Det gick inte att läsa in provet på nytt. Försök igen.";

function nextItemId(items: NativeExamItem[]): string {
  const usedIds = new Set(items.map((item) => item.item_id));
  let highest = 0;
  for (const item of items) {
    const match = /^item_(\d+)$/.exec(item.item_id);
    if (match) {
      highest = Math.max(highest, Number(match[1]));
    }
  }
  let candidate = highest + 1;
  while (usedIds.has(`item_${String(candidate).padStart(3, "0")}`)) {
    candidate += 1;
  }
  return `item_${String(candidate).padStart(3, "0")}`;
}

export function useExamWorkspaceDocument() {
  const toast = useToast();

  const workspaceDocument = ref<NativeExamDocument | null>(null);
  const summary = ref<ExamWorkspaceDocumentSummary | null>(null);
  const notes = ref<string[]>([]);
  const isDirty = ref(false);
  const isBusy = ref(false);
  const conflictNotice = ref<string | null>(null);
  const selectedItemId = ref<string | null>(null);

  const selectedItem = computed<NativeExamItem | null>(() => {
    const current = workspaceDocument.value;
    if (!current || selectedItemId.value === null) {
      return null;
    }
    return current.items.find((item) => item.item_id === selectedItemId.value) ?? null;
  });

  const isExportReady = computed(() => {
    const current = workspaceDocument.value;
    if (!current || isDirty.value) {
      return false;
    }
    return current.items.every((item) => item.review.state === "review_complete");
  });

  function applyResponse(response: ExamWorkspaceDocumentResponse): void {
    workspaceDocument.value = response.document;
    summary.value = response.summary;
    notes.value = response.notes;
    isDirty.value = false;
    const items = response.document.items;
    selectedItemId.value = items.some((item) => item.item_id === selectedItemId.value)
      ? selectedItemId.value
      : (items[0]?.item_id ?? null);
  }

  async function importDocument(file: File): Promise<void> {
    if (isBusy.value) {
      return;
    }
    isBusy.value = true;
    try {
      const response = await requestImportExamWorkspaceDocument(file);
      selectedItemId.value = null;
      applyResponse(response);
      conflictNotice.value = null;
      toast.success(IMPORT_SUCCESS_COPY);
    } catch {
      toast.failure(IMPORT_FAILURE_COPY);
    } finally {
      isBusy.value = false;
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

  async function saveDocument(): Promise<void> {
    const current = workspaceDocument.value;
    const currentSummary = summary.value;
    if (!current || !currentSummary || isBusy.value) {
      return;
    }
    const expectedRevision = current.revision;
    const payload: NativeExamDocument = { ...current, revision: expectedRevision + 1 };
    isBusy.value = true;
    try {
      const response = await requestSaveExamWorkspaceDocument(currentSummary.lineage_id, {
        document: payload,
        expectedRevision,
      });
      applyResponse(response);
      conflictNotice.value = null;
      toast.success(SAVE_SUCCESS_COPY);
    } catch (error) {
      if (isApiError(error) && error.status === 409) {
        conflictNotice.value = EXAM_WORKSPACE_CONFLICT_COPY;
        toast.failure(EXAM_WORKSPACE_CONFLICT_COPY);
        await reloadAfterConflict(currentSummary.lineage_id);
      } else {
        toast.failure(SAVE_FAILURE_COPY);
      }
    } finally {
      isBusy.value = false;
    }
  }

  async function reloadDocument(): Promise<void> {
    const currentSummary = summary.value;
    if (!currentSummary || isBusy.value) {
      return;
    }
    isBusy.value = true;
    try {
      const response = await getExamWorkspaceDocument(currentSummary.lineage_id);
      applyResponse(response);
      conflictNotice.value = null;
      toast.info(RELOAD_SUCCESS_COPY);
    } catch {
      toast.failure(RELOAD_FAILURE_COPY);
    } finally {
      isBusy.value = false;
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
    if (!current) {
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

  function updateItemPoints(itemId: string, points: number | null): void {
    patchItem(itemId, (item) => ({ ...item, points }));
  }

  function updateItemBodyText(
    itemId: string,
    paragraphIndex: number,
    segmentIndex: number,
    text: string,
  ): void {
    patchItem(itemId, (item) => ({
      ...item,
      body: item.body.map((paragraph, candidateParagraphIndex) => {
        if (candidateParagraphIndex !== paragraphIndex) {
          return paragraph;
        }
        return {
          segments: paragraph.segments.map((segment, candidateSegmentIndex) =>
            candidateSegmentIndex === segmentIndex && segment.kind === "text"
              ? { ...segment, text }
              : segment,
          ),
        };
      }),
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
        correct_choice_ids: correctChoiceIds,
        origin: "teacher_authored",
      },
    }));
  }

  function updateItemGapValues(
    itemId: string,
    gapId: string,
    acceptedValues: string[],
  ): void {
    patchItem(itemId, (item) => ({
      ...item,
      answer_key: { ...item.answer_key, origin: "teacher_authored" },
      gaps: item.gaps.map((gap) =>
        gap.gap_id === gapId ? { ...gap, accepted_values: acceptedValues } : gap,
      ),
    }));
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

  function addItem(): void {
    const current = workspaceDocument.value;
    if (!current) {
      return;
    }
    const itemId = nextItemId(current.items);
    const newItem: NativeExamItem = {
      answer_key: { correct_choice_ids: [], origin: "not_applicable" },
      body: [{ segments: [{ kind: "text", text: "Ny fråga" }] }],
      choices: [],
      gaps: [],
      item_id: itemId,
      kind: "free_text",
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
    conflictNotice,
    importDocument,
    isBusy,
    isDirty,
    isExportReady,
    markItemReviewed,
    notes,
    reloadDocument,
    saveDocument,
    selectItem,
    selectedItem,
    selectedItemId,
    summary,
    updateItemBodyText,
    updateItemChoiceText,
    updateItemCorrectChoices,
    updateItemGapValues,
    updateItemPoints,
    updateItemTitle,
    workspaceDocument,
  };
}
