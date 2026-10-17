/**
 * Exam workspace selection and navigation.
 *
 * Domain purpose:
 *   Know which list entry (a question, or an instruction the teacher
 *   selected) the editor shows, derive the list entries, readiness, totals
 *   and the selected unit's context (its instruction, position and notice),
 *   and move between entries by selection, step, jump and reorder.
 *
 * Relationships:
 *   - Reads the document, the selected question and the structure notices
 *     from `useExamWorkspaceEditing`.
 *   - Clears the Import box and the phone list through the refs the view
 *     owns; `afterGoto` lets the view settle its drawer after a jump.
 *   - Consumed by `ExamWorkspaceView` and the export, save and keyboard
 *     composables through the view.
 */

import { computed, ref, watch } from "vue";
import type { Ref } from "vue";

import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import type { ExamWorkspaceReadinessReason } from "./examWorkspaceItemReadiness";
import { examWorkspaceListEntries, examWorkspaceListTotal } from "./examWorkspaceListEntries";
import type { ExamWorkspaceItemEntry, ExamWorkspaceParentEntry } from "./examWorkspaceListEntries";
import { bodyText } from "./examWorkspaceRichText";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

export interface ExamWorkspaceSelectionDeps {
  editing: ReturnType<typeof useExamWorkspaceEditing>;
  importOpen: Ref<boolean>;
  listOpen: Ref<boolean>;
  /** Runs after a jump to a question, so the view can settle its drawer. */
  afterGoto: () => void;
}

export function useExamWorkspaceSelection({ editing, importOpen, listOpen, afterGoto }: ExamWorkspaceSelectionDeps) {
  const { structure, workspaceDocument, convertingItemIds, selectedItemId, selectItem } = editing;

  /** An instruction the teacher selected; its first question stays the document's selection. */
  const selectedParentId = ref<string | null>(null);

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

  const selectedEntryId = computed(() => selectedParentId.value ?? selectedItemId.value);
  const selectedEntry = computed(() => entries.value.find((entry) => entry.id === selectedEntryId.value) ?? null);
  const selectedItem = computed(() =>
    selectedParentId.value === null ? (items.value.find((item) => item.item_id === selectedItemId.value) ?? null) : null,
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
  const entryIndex = computed(() => entries.value.findIndex((entry) => entry.id === selectedEntryId.value));
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

  function selectEntry(id: string): void {
    structure.dismissDeleteNotice();
    importOpen.value = false;
    if (workspaceDocument.value?.parents.some((parent) => parent.parent_id === id)) {
      selectedParentId.value = id;
    } else {
      selectedParentId.value = null;
      selectItem(id);
    }
    listOpen.value = false;
  }

  function step(delta: -1 | 1): void {
    const target = entries.value[entryIndex.value + delta];
    if (target) selectEntry(target.id);
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
  watch(selectedItemId, () => {
    selectedParentId.value = null;
    importOpen.value = false;
  });

  return {
    converting,
    dismissItemNotice,
    entries,
    entryIndex,
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
