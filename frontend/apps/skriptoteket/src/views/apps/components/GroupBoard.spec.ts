import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GroupBoard from "./GroupBoard.vue";

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    ungroupedStudents: [{ id: "student-1", display_name: "Ada" }],
    groups: [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }],
    canUndo: false,
    canRedo: false,
    isWorkspaceBusy: false,
    studentsByGroupId: {
      "group-a": [{ id: "student-2", display_name: "Bo" }],
    },
    groupAssignments: [{ student_id: "student-2", group_id: "group-a" }],
    addGroup: vi.fn(),
    randomizeGroups: vi.fn(),
    clearGroupingAssignments: vi.fn(),
    undoGroupingDraft: vi.fn(),
    redoGroupingDraft: vi.fn(),
    assignStudentToGroup: vi.fn(),
    removeStudentFromGroup: vi.fn(),
    renameGroup: vi.fn(),
    moveGroup: vi.fn(),
    removeGroup: vi.fn(),
    seatAssignmentsByStudentId: {
      "student-1": "seat-1",
      "student-2": "seat-2",
    },
  },
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("GroupBoard", () => {
  beforeEach(() => {
    stateMocks.plannerState.addGroup.mockReset();
    stateMocks.plannerState.randomizeGroups.mockReset();
    stateMocks.plannerState.clearGroupingAssignments.mockReset();
    stateMocks.plannerState.undoGroupingDraft.mockReset();
    stateMocks.plannerState.redoGroupingDraft.mockReset();
    stateMocks.plannerState.canUndo = false;
    stateMocks.plannerState.canRedo = false;
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.groupAssignments = [{ student_id: "student-2", group_id: "group-a" }];
  });

  it("does not leak seat labels into the grouping surface", () => {
    const wrapper = mount(GroupBoard);

    expect(wrapper.text()).toContain("Ej grupperade");
    expect(wrapper.text()).not.toContain("Plats");
    expect(wrapper.text()).not.toContain("seat-1");
    expect(wrapper.text()).not.toContain("seat-2");
  });

  it("exposes grouping-only workspace controls", async () => {
    const wrapper = mount(GroupBoard);

    await wrapper.get('[data-test="randomize-groups"]').trigger("click");
    expect(stateMocks.plannerState.randomizeGroups).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-test="add-group"]').trigger("click");
    expect(stateMocks.plannerState.addGroup).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-test="new-grouping-draft"]').trigger("click");
    expect(wrapper.emitted("new-grouping-draft")).toEqual([[]]);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="grouping-history"]').trigger("click");
    expect(wrapper.emitted("open-history")).toEqual([[]]);

    await wrapper.get('[data-test="grouping-actions-menu"]').trigger("click");
    await wrapper.get('[data-test="edit-grouping-roster"]').trigger("click");
    expect(wrapper.emitted("edit-roster")).toEqual([[]]);
  });

  it("uses backend-owned undo and redo availability", async () => {
    stateMocks.plannerState.canUndo = true;
    stateMocks.plannerState.canRedo = true;
    const wrapper = mount(GroupBoard);

    const undoButton = wrapper.get('[data-test="undo-grouping"]');
    const redoButton = wrapper.get('[data-test="redo-grouping"]');

    expect((undoButton.element as HTMLButtonElement).disabled).toBe(false);
    expect((redoButton.element as HTMLButtonElement).disabled).toBe(false);

    await undoButton.trigger("click");
    await redoButton.trigger("click");

    expect(stateMocks.plannerState.undoGroupingDraft).toHaveBeenCalledTimes(1);
    expect(stateMocks.plannerState.redoGroupingDraft).toHaveBeenCalledTimes(1);
  });

  it("confirms before clearing the current grouping draft in place", async () => {
    const wrapper = mount(GroupBoard);

    await wrapper.get('[data-test="reset-grouping-draft"]').trigger("click");

    expect(wrapper.text()).toContain("Töm gruppindelningen?");

    await wrapper.get('[data-test="confirm-dialog-confirm"]').trigger("click");

    expect(stateMocks.plannerState.clearGroupingAssignments).toHaveBeenCalledTimes(1);
    expect(wrapper.emitted("new-grouping-draft")).toBeUndefined();
  });

  it("locks grouping interactions while the workspace is transitioning", () => {
    stateMocks.plannerState.isWorkspaceBusy = true;
    const wrapper = mount(GroupBoard);

    expect((wrapper.get('[data-test="new-grouping-draft"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-test="randomize-groups"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-test="reset-grouping-draft"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('[data-test="add-group"]').element as HTMLButtonElement).disabled).toBe(true);
    expect((wrapper.get('input[type="text"]').element as HTMLInputElement).disabled).toBe(true);
  });

  it("disables börja om when there is nothing to clear", () => {
    stateMocks.plannerState.groupAssignments = [];
    const wrapper = mount(GroupBoard);

    expect((wrapper.get('[data-test="reset-grouping-draft"]').element as HTMLButtonElement).disabled).toBe(true);
  });
});
