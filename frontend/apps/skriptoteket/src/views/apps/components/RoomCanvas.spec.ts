import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RoomFixture } from "../classroomPlannerTypes";
import RoomCanvas from "./RoomCanvas.vue";

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    unseatedStudents: [{ id: "student-1", display_name: "Ada" }],
    template: { id: "template-1", name: "Sal 101", grid_cols: 14, grid_rows: 9, seats: [], fixtures: [] },
    seats: [{ id: "seat-1", x: 0, y: 0 }],
    fixtures: [] as RoomFixture[],
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
    stateMocks.plannerState.fixtures = [];
  });

  it("keeps the seating surface free from grouping labels", () => {
    const wrapper = mount(RoomCanvas);

    expect(wrapper.text()).toContain("Sittschema");
    expect(wrapper.text()).not.toContain("Grupp A");
  });

  it("shows labels only for fixtures that need them", () => {
    stateMocks.plannerState.fixtures = [
      {
        id: "fixture-1",
        type: "teacher_desk",
        x: 96,
        y: 96,
        width: 192,
        height: 96,
        label: "Kateder",
      },
      {
        id: "fixture-2",
        type: "whiteboard",
        x: 0,
        y: 0,
        width: 288,
        height: 96,
        label: "Whiteboard",
      },
      {
        id: "fixture-3",
        type: "door",
        x: 0,
        y: 384,
        width: 96,
        height: 96,
        label: null,
      },
    ];

    const wrapper = mount(RoomCanvas);

    expect(wrapper.text()).toContain("Kateder");
    expect(wrapper.text()).toContain("Whiteboard");
    expect(wrapper.text()).not.toContain("Dörr");
  });

  it("renders seats as circular tokens in the live seating canvas", () => {
    const wrapper = mount(RoomCanvas);

    expect(wrapper.html()).toContain("rounded-full");
  });
});
