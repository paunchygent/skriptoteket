import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GroupBoard from "./GroupBoard.vue";

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    ungroupedStudents: [{ id: "student-1", display_name: "Ada" }],
    groups: [{ id: "group-a", name: "Grupp A", sort_order: 0 }],
    studentsByGroupId: {
      "group-a": [{ id: "student-2", display_name: "Bo" }],
    },
    addGroup: vi.fn(),
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
  });

  it("does not leak seat labels into the grouping surface", () => {
    const wrapper = mount(GroupBoard);

    expect(wrapper.text()).toContain("Ej grupperade");
    expect(wrapper.text()).not.toContain("Plats");
    expect(wrapper.text()).not.toContain("seat-1");
    expect(wrapper.text()).not.toContain("seat-2");
  });
});
