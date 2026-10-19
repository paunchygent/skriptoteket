/**
 * Exam workspace question-list actions.
 *
 * Domain purpose:
 *   Own the view's question-list commands (TASK-SKRIPT-41-02-04): saving the
 *   list ordering with rollback and its exact failure copy, marking questions
 *   reviewed, and adding entries and children through the structure commands.
 *
 * Relationships:
 *   - Consumed by `ExamWorkspaceView` with the editing, selection and shell
 *     state it already holds.
 */

import type { ComputedRef, Ref } from "vue";

import type { ExamListOrdering, NativeExamItem } from "../../../api/examWorkspace";
import { isTeacherReviewed, type TeacherItemKind } from "./examWorkspaceItemEdits";

export type ExamWorkspaceListActionsDeps = {
  store: {
    teacher: { updateExamListOrdering(ordering: ExamListOrdering): Promise<void> } | null;
  };
  listOrdering: Ref<ExamListOrdering>;
  toast: { failure(message: string): void };
  editing: {
    markItemReviewed(itemId: string): void;
    unmarkItemReviewed(itemId: string): void;
  };
  structure: {
    addInstruction(): Promise<void>;
    addEmptyPart(): Promise<void>;
    addItem(kind: TeacherItemKind): void;
    addChild(parentId: string, kind: TeacherItemKind): Promise<void>;
  };
  selectedItem: ComputedRef<NativeExamItem | null>;
  selectedParentId: Ref<string | null>;
  listOpen: Ref<boolean>;
};

export type ExamWorkspaceListActions = {
  setOrdering(ordering: ExamListOrdering): Promise<void>;
  toggleReviewed(): void;
  addEntry(kind: TeacherItemKind | "instruction" | "part"): void;
  addChild(kind: TeacherItemKind): void;
};

export function useExamWorkspaceListActions(deps: ExamWorkspaceListActionsDeps): ExamWorkspaceListActions {
  async function setOrdering(ordering: ExamListOrdering): Promise<void> {
    const teacher = deps.store.teacher;
    if (!teacher) return;
    const previous = deps.listOrdering.value;
    deps.listOrdering.value = ordering;
    try {
      await teacher.updateExamListOrdering(ordering);
    } catch {
      deps.listOrdering.value = previous;
      deps.toast.failure("Ordningen kunde inte sparas. Försök igen.");
    }
  }

  function toggleReviewed(): void {
    const item = deps.selectedItem.value;
    if (!item) return;
    if (isTeacherReviewed(item)) {
      deps.editing.unmarkItemReviewed(item.item_id);
    } else {
      deps.editing.markItemReviewed(item.item_id);
    }
  }

  function addEntry(kind: TeacherItemKind | "instruction" | "part"): void {
    deps.listOpen.value = false;
    if (kind === "instruction") {
      void deps.structure.addInstruction();
    } else if (kind === "part") {
      void deps.structure.addEmptyPart();
    } else {
      deps.structure.addItem(kind);
    }
  }

  function addChild(kind: TeacherItemKind): void {
    if (deps.selectedParentId.value) void deps.structure.addChild(deps.selectedParentId.value, kind);
  }

  return { addChild, addEntry, setOrdering, toggleReviewed };
}
