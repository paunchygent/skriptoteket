/**
 * Exam workspace question-list actions.
 *
 * Expected behavior:
 *   `setOrdering` saves the chosen ordering and leaves the toast silent; a
 *   failed save restores the previous ordering and reports the exact
 *   rollback copy, and a guest (no teacher) changes nothing. `toggleReviewed`
 *   marks an unreviewed question, unmarks a reviewed one, and does nothing
 *   without a selection. `addEntry` closes the phone list layer and dispatches
 *   instructions, parts and question kinds to their structure command.
 *   `addChild` adds under the selected parent and does nothing without one.
 */

import { describe, expect, it, vi } from "vitest";
import { computed, ref } from "vue";

import type { ExamListOrdering, NativeExamItem } from "../../../api/examWorkspace";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import { reviewed, unreviewed, type TeacherItemKind } from "./examWorkspaceItemEdits";
import { useExamWorkspaceListActions } from "./useExamWorkspaceListActions";

function arrange(params: {
  item?: NativeExamItem | null;
  parentId?: string | null;
  ordering?: ExamListOrdering;
  teacher?: "signed-in" | "guest";
  saveFails?: boolean;
} = {}) {
  const updateExamListOrdering = params.saveFails
    ? vi.fn(async (): Promise<void> => {
      throw new Error("offline");
    })
    : vi.fn(async (): Promise<void> => {});
  const failure = vi.fn();
  const markItemReviewed = vi.fn();
  const unmarkItemReviewed = vi.fn();
  const addInstruction = vi.fn(async (): Promise<void> => {});
  const addEmptyPart = vi.fn(async (): Promise<void> => {});
  const addItem = vi.fn();
  const addChild = vi.fn(async (): Promise<void> => {});
  const listOrdering = ref<ExamListOrdering>(params.ordering ?? "course");
  const item = ref<NativeExamItem | null>(params.item ?? null);
  const selectedItem = computed(() => item.value);
  const selectedParentId = ref<string | null>(params.parentId ?? null);
  const listOpen = ref(true);
  const actions = useExamWorkspaceListActions({
    editing: { markItemReviewed, unmarkItemReviewed },
    listOpen,
    listOrdering,
    selectedItem,
    selectedParentId,
    store: params.teacher === "guest"
      ? { teacher: null }
      : { teacher: { updateExamListOrdering } },
    structure: { addChild, addEmptyPart, addInstruction, addItem },
    toast: { failure },
  });
  return {
    actions,
    addChild,
    addEmptyPart,
    addInstruction,
    addItem,
    failure,
    listOpen,
    listOrdering,
    markItemReviewed,
    unmarkItemReviewed,
    updateExamListOrdering,
  };
}

describe("useExamWorkspaceListActions", () => {
  it("saves the chosen ordering without a toast", async () => {
    const arranged = arrange();

    await arranged.actions.setOrdering("newest");

    expect(arranged.updateExamListOrdering).toHaveBeenCalledWith("newest");
    expect(arranged.listOrdering.value).toBe("newest");
    expect(arranged.failure).not.toHaveBeenCalled();
  });

  it("restores the previous ordering and toasts the exact rollback copy when saving fails", async () => {
    const arranged = arrange({ ordering: "course", saveFails: true });

    await arranged.actions.setOrdering("newest");

    expect(arranged.listOrdering.value).toBe("course");
    expect(arranged.failure).toHaveBeenCalledWith("Ordningen kunde inte sparas. Försök igen.");
  });

  it("leaves a guest's ordering untouched", async () => {
    const arranged = arrange({ teacher: "guest" });

    await arranged.actions.setOrdering("newest");

    expect(arranged.updateExamListOrdering).not.toHaveBeenCalled();
    expect(arranged.listOrdering.value).toBe("course");
    expect(arranged.failure).not.toHaveBeenCalled();
  });

  it("marks an unreviewed question as reviewed", () => {
    const item = unreviewed(buildFreeTextItem(1));
    const arranged = arrange({ item });

    arranged.actions.toggleReviewed();

    expect(arranged.markItemReviewed).toHaveBeenCalledWith(item.item_id);
    expect(arranged.unmarkItemReviewed).not.toHaveBeenCalled();
  });

  it("unmarks a reviewed question", () => {
    const item = reviewed(buildFreeTextItem(1));
    const arranged = arrange({ item });

    arranged.actions.toggleReviewed();

    expect(arranged.unmarkItemReviewed).toHaveBeenCalledWith(item.item_id);
    expect(arranged.markItemReviewed).not.toHaveBeenCalled();
  });

  it("does nothing without a selection", () => {
    const arranged = arrange({ item: null });

    arranged.actions.toggleReviewed();

    expect(arranged.markItemReviewed).not.toHaveBeenCalled();
    expect(arranged.unmarkItemReviewed).not.toHaveBeenCalled();
  });

  it("closes the list layer and dispatches instructions, parts and question kinds", () => {
    const arranged = arrange();

    arranged.actions.addEntry("instruction");
    arranged.actions.addEntry("part");
    const kind: TeacherItemKind = "single_choice";
    arranged.actions.addEntry(kind);

    expect(arranged.listOpen.value).toBe(false);
    expect(arranged.addInstruction).toHaveBeenCalledTimes(1);
    expect(arranged.addEmptyPart).toHaveBeenCalledTimes(1);
    expect(arranged.addItem).toHaveBeenCalledWith(kind);
  });

  it("adds under the selected parent and does nothing without one", () => {
    const withParent = arrange({ parentId: "parent-1" });
    withParent.actions.addChild("single_choice");
    expect(withParent.addChild).toHaveBeenCalledWith("parent-1", "single_choice");

    const withoutParent = arrange({ parentId: null });
    withoutParent.actions.addChild("single_choice");
    expect(withoutParent.addChild).not.toHaveBeenCalled();
  });
});
