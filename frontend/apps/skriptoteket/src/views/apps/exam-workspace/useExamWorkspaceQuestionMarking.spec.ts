/**
 * Exam workspace question list, Markera mode state.
 *
 * Expected behavior:
 *   Toggling the mode on starts with no ticks and toggling it off clears
 *   them. Only standalone questions count as ticks: a part and a question
 *   inside a part are ignored even when their ids were ticked, and the ticks
 *   come in document order whatever order they were ticked in (G10, G11).
 *   Ticking waits while the workspace is busy. The group command passes the
 *   ordered ticks and does nothing without ticks. When the entries no longer
 *   hold a tick as a standalone question (an accepted group), the mode
 *   leaves; a refused group keeps the mode and the ticks.
 */

import { nextTick, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import type { ExamWorkspaceItemEntry, ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { useExamWorkspaceQuestionMarking } from "./useExamWorkspaceQuestionMarking";

function question(id: string, parentId: string | null = null): ExamWorkspaceItemEntry {
  return {
    aiKey: null,
    id,
    itemKind: "free_text",
    kind: "item",
    label: id,
    parentId,
    points: 1,
    problem: null,
    status: "ok",
    text: `Text ${id}`,
    typeLabel: "Fritext",
  };
}

const ENTRIES: ExamWorkspaceListEntry[] = [
  question("item_001"),
  { childIds: ["item_002"], id: "parent_001", kind: "parent", label: "2", points: 2, text: "Delinstruktion" },
  question("item_002", "parent_001"),
  question("item_003"),
];

function setup(disabled = false) {
  const entries = ref<ExamWorkspaceListEntry[]>(ENTRIES);
  const busy = ref(disabled);
  const onGroup = vi.fn();
  const state = useExamWorkspaceQuestionMarking({
    entries: () => entries.value,
    disabled: () => busy.value,
    onGroup,
  });
  return { busy, entries, onGroup, state };
}

describe("useExamWorkspaceQuestionMarking", () => {
  it("starts empty, enters the mode with no ticks and clears the ticks when the mode is left", () => {
    const { state } = setup();
    expect(state.marking.value).toBe(false);

    state.toggleMarking();
    state.toggleMark("item_001");
    expect(state.marking.value).toBe(true);
    expect(state.markedIds.value).toEqual(["item_001"]);

    state.toggleMarking();
    expect(state.marking.value).toBe(false);
    expect(state.marked.value.size).toBe(0);

    state.toggleMarking();
    expect(state.markedIds.value).toEqual([]);
  });

  it("counts only standalone questions, in document order, and unticks on a second press", () => {
    const { state } = setup();
    state.toggleMarking();

    state.toggleMark("item_003");
    state.toggleMark("item_002");
    state.toggleMark("parent_001");
    state.toggleMark("item_001");
    expect(state.markedIds.value).toEqual(["item_001", "item_003"]);

    state.toggleMark("item_003");
    expect(state.markedIds.value).toEqual(["item_001"]);
  });

  it("ignores ticks while the workspace is busy", () => {
    const { busy, state } = setup(true);
    state.toggleMarking();

    state.toggleMark("item_001");
    expect(state.markedIds.value).toEqual([]);

    busy.value = false;
    state.toggleMark("item_001");
    expect(state.markedIds.value).toEqual(["item_001"]);
  });

  it("passes the ordered ticks to the group command and does nothing without ticks", () => {
    const { onGroup, state } = setup();
    state.toggleMarking();

    state.groupMarked();
    expect(onGroup).not.toHaveBeenCalled();

    state.toggleMark("item_003");
    state.toggleMark("item_001");
    state.groupMarked();
    expect(onGroup).toHaveBeenCalledExactlyOnceWith(["item_001", "item_003"]);
  });

  it("keeps the mode and the ticks after a refused group", async () => {
    const { onGroup, state } = setup();
    state.toggleMarking();
    state.toggleMark("item_001");

    state.groupMarked();
    await nextTick();

    expect(onGroup).toHaveBeenCalledTimes(1);
    expect(state.marking.value).toBe(true);
    expect(state.markedIds.value).toEqual(["item_001"]);
  });

  it("leaves the mode when an accepted group moves every tick into a part", async () => {
    const { entries, state } = setup();
    state.toggleMarking();
    state.toggleMark("item_001");
    state.toggleMark("item_003");

    entries.value = [
      { childIds: ["item_001", "item_003"], id: "parent_002", kind: "parent", label: "1", points: 2, text: "" },
      question("item_001", "parent_002"),
      question("item_003", "parent_002"),
    ];
    await nextTick();

    expect(state.marking.value).toBe(false);
    expect(state.marked.value.size).toBe(0);
  });
});
