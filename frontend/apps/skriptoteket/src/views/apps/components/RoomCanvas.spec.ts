import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RoomFixture, Student } from "../classroomPlannerTypes";
import RoomCanvas from "./RoomCanvas.vue";

class ResizeObserverMock {
  observe(): void {}
  disconnect(): void {}
}

function setViewportSize(width: number, height: number): void {
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get: () => width,
  });
  Object.defineProperty(HTMLElement.prototype, "clientHeight", {
    configurable: true,
    get: () => height,
  });
}

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    unseatedStudents: [{ id: "student-1", display_name: "Ada" }],
    template: { id: "template-1", name: "Sal 101", grid_cols: 14, grid_rows: 9, seats: [], fixtures: [] },
    seats: [{ id: "seat-1", x: 0, y: 0 }],
    fixtures: [] as RoomFixture[],
    studentBySeatId: { "seat-1": null } as Record<string, Student | null>,
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
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    setViewportSize(1200, 800);
    stateMocks.plannerState.assignStudentToSeat.mockReset();
    stateMocks.plannerState.clearSeatAssignment.mockReset();
    stateMocks.plannerState.swapSeatAssignments.mockReset();
    stateMocks.plannerState.fixtures = [];
    stateMocks.plannerState.studentBySeatId = { "seat-1": null };
  });

  it("keeps the seating surface free from grouping labels", () => {
    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        surfaceScale: 1,
      },
    });

    expect(wrapper.text()).toContain("Sittschema");
    expect(wrapper.text()).not.toContain("Grupp A");
  });

  it("renders shared presentation labels and merged seating-scene fixtures", () => {
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
      {
        id: "fixture-4",
        type: "bench",
        x: 384,
        y: 384,
        width: 96,
        height: 96,
        label: null,
      },
      {
        id: "fixture-5",
        type: "bench",
        x: 480,
        y: 384,
        width: 96,
        height: 96,
        label: null,
      },
    ];

    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        surfaceScale: 1,
      },
    });

    expect(wrapper.text()).toContain("Kateder");
    expect(wrapper.text()).toContain("Whiteboard");
    expect(wrapper.text()).toContain("Dörr");
    expect(wrapper.text().match(/Bänk/g)).toHaveLength(1);
  });

  it("renders seats as circular tokens in the live seating canvas", () => {
    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        surfaceScale: 1,
      },
    });

    expect(wrapper.html()).toContain("rounded-full");
  });

  it("renders tile markers for visible smart rules on occupied seats", () => {
    stateMocks.plannerState.studentBySeatId = {
      "seat-1": { id: "student-1", display_name: "Ada" },
    };

    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        selectedStudentIds: ["student-1"],
        smartRuleMarkersByStudentId: {
          "student-1": ["Lärare", "Isär A"],
        },
        surfaceScale: 1,
      },
    });

    expect(wrapper.get('[data-test="seat-markers-seat-1"]').text()).toContain("Lärare");
    expect(wrapper.get('[data-test="seat-markers-seat-1"]').text()).toContain("Isär A");
  });

  it("renders seating zoom controls and forwards the viewport actions", async () => {
    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 80,
        scaledSurfaceStyle: { width: "1120px", height: "768px" },
        surfaceScale: 0.8,
      },
    });

    expect(wrapper.get('[data-test="seating-zoom-percent"]').text()).toContain("80%");

    await wrapper.get('[data-test="seating-zoom-out"]').trigger("click");
    await wrapper.get('[data-test="seating-zoom-in"]').trigger("click");
    await wrapper.get('[data-test="seating-zoom-fit"]').trigger("click");

    expect(wrapper.emitted("zoom-out")).toHaveLength(1);
    expect(wrapper.emitted("zoom-in")).toHaveLength(1);
    expect(wrapper.emitted("zoom-fit")).toHaveLength(1);
    expect(wrapper.emitted("viewport-size")).toBeTruthy();
  });

  it("anchors the zoomed seating surface to the left edge when it overflows horizontally", async () => {
    setViewportSize(800, 600);

    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 80,
        scaledSurfaceStyle: { width: "1120px", height: "768px" },
        surfaceScale: 0.8,
      },
    });

    await nextTick();

    expect(wrapper.get('[data-test="room-canvas-scroll-frame"]').attributes("data-overflow-anchor")).toBe("start");
  });
});
