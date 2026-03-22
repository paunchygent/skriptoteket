import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GroupBoard from "./GroupBoard.vue";

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    ungroupedStudents: [{ id: "student-1", display_name: "Ada" }],
    groups: [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }],
    studentsByGroupId: {
      "group-a": [{ id: "student-2", display_name: "Bo" }],
    },
    addGroup: vi.fn(),
    randomizeGroups: vi.fn(),
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
  });
});
