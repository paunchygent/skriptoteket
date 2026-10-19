/**
 * Exam workspace selection and navigation.
 *
 * Domain purpose:
 *   Know which list entry (a question, an instruction the teacher
 *   selected, or the exam instruction) the editor shows, derive the list entries, readiness, totals
 *   and the selected unit's context (its instruction, position and notice),
 *   and move between entries by selection, step, jump and reorder. Leaving a
 *   question removes its empty gaps silently as one structural edit with no
 *   toast, through the ordinary item edit path.
 *
 * Relationships:
 *   - Reads the document, the selected question and the structure notices
 *     from `useExamWorkspaceEditing`; it drives that session's shared
 *     `selectedParentId` so a structural insert lands after the part entry the
 *     teacher selected.
 *   - Clears the Import box and the phone list through the refs the view
 *     owns; `afterGoto` lets the view settle its drawer after a jump.
 *   - Consumed by `ExamWorkspaceView` and the export, save and keyboard
 *     composables through the view.
 */

import { computed, onScopeDispose, ref, watch } from "vue";
import type { Ref } from "vue";

import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import type { ExamWorkspaceReadinessReason } from "./examWorkspaceItemReadiness";
import { examWorkspaceListEntries, examWorkspaceListTotal } from "./examWorkspaceListEntries";
import type { ExamWorkspaceItemEntry, ExamWorkspaceParentEntry } from "./examWorkspaceListEntries";
import { bodyText } from "./examWorkspaceRichText";
import { isEmptyBody } from "./examWorkspaceRichTextDocument";
import { bodyWithoutEmptyGaps } from "./useExamWorkspaceMakeGap";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

/** The list entry that opens the exam instruction; it is neither a question nor an instruction with deluppgifter. */
export const EXAM_INSTRUCTIONS_ENTRY_ID = "exam_instructions";

export interface ExamWorkspaceSelectionDeps {
  editing: ReturnType<typeof useExamWorkspaceEditing>;
  importOpen: Ref<boolean>;
  listOpen: Ref<boolean>;
  /** Runs after a jump to a question, so the view can settle its drawer. */
  afterGoto: () => void;
}

export function useExamWorkspaceSelection({ editing, importOpen, listOpen, afterGoto }: ExamWorkspaceSelectionDeps) {
  const { structure, workspaceDocument, convertingItemIds, selectedItemId, selectedParentId, selectItem } = editing;

  /** The exam instruction the teacher selected; the document's selected question stays behind it. */
  const examInstructionsSelected = ref(false);

  const items = computed(() => workspaceDocument.value?.items ?? []);
  const readiness = computed<Record<string, ExamWorkspaceReadinessReason[]>>(() =>
    Object.fromEntries(items.value.map((item) => [item.item_id, examWorkspaceItemReadiness(item)])),
  );
  const entries = computed(() =>
    workspaceDocument.value
      ? examWorkspaceListEntries(workspaceDocument.value, readiness.value, convertingItemIds.value)
      : [],
  );
  const itemEntries = computed(() =>
    entries.value.filter((entry): entry is ExamWorkspaceItemEntry => entry.kind === "item"),
  );
  const total = computed(() => examWorkspaceListTotal(entries.value));

  const selectedEntryId = computed(() =>
    examInstructionsSelected.value ? EXAM_INSTRUCTIONS_ENTRY_ID : (selectedParentId.value ?? selectedItemId.value),
  );
  const selectedEntry = computed(() => entries.value.find((entry) => entry.id === selectedEntryId.value) ?? null);
  const selectedItem = computed(() =>
    selectedParentId.value === null && !examInstructionsSelected.value
      ? (items.value.find((item) => item.item_id === selectedItemId.value) ?? null)
      : null,
  );
  const selectedParent = computed(
    () => workspaceDocument.value?.parents.find((parent) => parent.parent_id === selectedParentId.value) ?? null,
  );
  const selectedParentEntry = computed(() =>
    selectedEntry.value?.kind === "parent" ? (selectedEntry.value as ExamWorkspaceParentEntry) : null,
  );
  const parentChildren = computed(() =>
    itemEntries.value.filter((entry) => entry.parentId === selectedParentId.value),
  );
  const itemEntry = computed(() =>
    selectedEntry.value?.kind === "item" ? (selectedEntry.value as ExamWorkspaceItemEntry) : null,
  );
  const itemParent = computed(() => {
    const parentId = itemEntry.value?.parentId ?? null;
    const parent = workspaceDocument.value?.parents.find((entry) => entry.parent_id === parentId);
    const entry = entries.value.find((candidate) => candidate.id === parentId);
    return parent && entry ? { id: parent.parent_id, label: entry.label, text: bodyText(parent.instruction) } : null;
  });
  const itemChild = computed(() => {
    const item = selectedItem.value;
    const parent = workspaceDocument.value?.parents.find((entry) => entry.item_ids.includes(item?.item_id ?? ""));
    return item && parent ? { index: parent.item_ids.indexOf(item.item_id), count: parent.item_ids.length } : null;
  });
  const itemNotice = computed<ExamWorkspaceNotice | null>(() => {
    const item = selectedItem.value;
    const typeNotice = structure.typeNotice.value;
    if (item && typeNotice && typeNotice.itemId === item.item_id && typeNotice.kind === item.kind) {
      return { kind: "type", text: typeNotice.text };
    }
    return structure.deleteNotice.value;
  });
  const converting = computed(
    () => selectedItem.value !== null && convertingItemIds.value.has(selectedItem.value.item_id),
  );
  const stripState = computed(() => {
    const entry = selectedEntry.value;
    if (!entry) return null;
    if (entry.kind === "parent") return "instruction" as const;
    return entry.status === "converting" ? ("converting" as const) : entry.status;
  });

  function dismissItemNotice(): void {
    if (itemNotice.value?.kind === "type") {
      structure.dismissTypeNotice();
    } else {
      structure.dismissDeleteNotice();
    }
  }

  function questionLabel(itemId: string): string | null {
    return itemEntries.value.find((entry) => entry.id === itemId)?.label ?? null;
  }

  /**
   * The empty-gap cleanup for leaving a question (TASK-SKRIPT-40-04-13 U4
   * rule 3): every empty gap in `itemId` is removed silently as one
   * structural edit with no toast, through the ordinary item edit path so it
   * autosaves like every step. A question without an answer key, any other
   * kind, or a question with no empty gaps emits nothing.
   */
  function removeEmptyGaps(itemId: string | null): void {
    if (itemId === null) {
      return;
    }
    const item = items.value.find((candidate) => candidate.item_id === itemId);
    if (!item) {
      return;
    }
    const cleaned = bodyWithoutEmptyGaps(item);
    if (cleaned === null) {
      return;
    }
    editing.updateItemBody(itemId, cleaned, true);
  }

  /** The open question, if the teacher is looking at one rather than an instruction. */
  function openQuestionId(): string | null {
    if (examInstructionsSelected.value || selectedParentId.value !== null) {
      return null;
    }
    return selectedItemId.value;
  }

  function selectEntry(id: string): void {
    const leaving = openQuestionId();
    if (leaving !== null && leaving !== id) {
      removeEmptyGaps(leaving);
    }
    structure.dismissDeleteNotice();
    importOpen.value = false;
    examInstructionsSelected.value = id === EXAM_INSTRUCTIONS_ENTRY_ID;
    if (examInstructionsSelected.value) {
      selectedParentId.value = null;
    } else if (workspaceDocument.value?.parents.some((parent) => parent.parent_id === id)) {
      selectedParentId.value = id;
    } else {
      selectedParentId.value = null;
      selectItem(id);
    }
    listOpen.value = false;
  }

  /**
   * The ids arrow keys and the phone strip walk, top to bottom: the exam
   * instruction sits above the first entry while the exam has one or it is open.
   */
  const stepOrder = computed(() => {
    const ids = entries.value.map((entry) => entry.id);
    const hasInstructions = !isEmptyBody(workspaceDocument.value?.instructions ?? []);
    return hasInstructions || examInstructionsSelected.value ? [EXAM_INSTRUCTIONS_ENTRY_ID, ...ids] : ids;
  });

  function stepTarget(delta: -1 | 1): string | null {
    const at = stepOrder.value.indexOf(selectedEntryId.value ?? "");
    return at < 0 ? null : (stepOrder.value[at + delta] ?? null);
  }

  function canStep(delta: -1 | 1): boolean {
    return stepTarget(delta) !== null;
  }

  function step(delta: -1 | 1): void {
    const target = stepTarget(delta);
    if (target !== null) selectEntry(target);
  }

  function gotoItem(itemId: string): void {
    selectEntry(itemId);
    afterGoto();
  }

  function moveSelected(delta: -1 | 1): void {
    const item = selectedItem.value;
    const parentId = itemEntry.value?.parentId;
    if (item && parentId) void structure.moveChild(parentId, item.item_id, delta);
  }

  // A deleted instruction cannot stay selected.
  watch(
    () => workspaceDocument.value?.parents,
    (parents) => {
      if (selectedParentId.value && !parents?.some((parent) => parent.parent_id === selectedParentId.value)) {
        selectedParentId.value = null;
      }
    },
  );

  // A command that selects a question (add, delete, a new exam) leaves the instruction.
  // Any question change from outside `selectEntry` (structure commands, whole-document
  // edits) leaves the previous question the same way; a repeat cleanup is a no-op.
  watch(selectedItemId, (next, previous) => {
    selectedParentId.value = null;
    examInstructionsSelected.value = false;
    importOpen.value = false;
    if (previous !== null && previous !== next) {
      removeEmptyGaps(previous);
    }
  });

  // Leaving the workspace route unmounts this scope: the open question's
  // empty gaps are removed the same way. This never runs on page unload.
  onScopeDispose(() => {
    removeEmptyGaps(openQuestionId());
  });

  // Another exam has its own instruction.
  watch(
    () => workspaceDocument.value?.document_id,
    () => {
      examInstructionsSelected.value = false;
    },
  );

  return {
    canStep,
    converting,
    dismissItemNotice,
    entries,
    examInstructionsSelected,
    gotoItem,
    itemChild,
    itemEntries,
    itemEntry,
    itemNotice,
    itemParent,
    items,
    moveSelected,
    parentChildren,
    questionLabel,
    readiness,
    selectedEntry,
    selectedEntryId,
    selectedItem,
    selectedParent,
    selectedParentEntry,
    selectedParentId,
    selectEntry,
    step,
    stripState,
    total,
  };
}
