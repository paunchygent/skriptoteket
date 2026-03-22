import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RoomCanvas from "./RoomCanvas.vue";

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    unseatedStudents: [{ id: "student-1", display_name: "Ada" }],
    seats: [{ id: "seat-1", x: 0, y: 0 }],
    fixtures: [],
    studentBySeatId: { "seat-1": null },
    assignStudentToSeat: vi.fn(),
    clearSeatAssignment: vi.fn(),
    swapSeatAssignments: vi.fn(),
    groupAssignmentsByStudentId: {
      "student-1": "group-a",
    },
    groupsById: {
      "group-a": { id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false },
    },
  },
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("RoomCanvas", () => {
  beforeEach(() => {
    stateMocks.plannerState.assignStudentToSeat.mockReset();
    stateMocks.plannerState.clearSeatAssignment.mockReset();
    stateMocks.plannerState.swapSeatAssignments.mockReset();
  });

  it("keeps the seating surface free from grouping labels", () => {
    const wrapper = mount(RoomCanvas);

    expect(wrapper.text()).toContain("Sittkarta");
    expect(wrapper.text()).not.toContain("Grupp A");
  });
});
