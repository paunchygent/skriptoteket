import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RoomFixture, RoomTemplate, Seat, SeatAssignment, Student } from "../classroomPlannerTypes";
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
    template: {
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [],
      fixtures: [],
    } as RoomTemplate,
    seats: [{ id: "seat-1", x: 0, y: 0 }] as Seat[],
    fixtures: [] as RoomFixture[],
    studentsById: {
      "student-1": { id: "student-1", display_name: "Ada" },
      "student-2": { id: "student-2", display_name: "Alan" },
    } as Record<string, Student | undefined>,
    seatAssignments: [] as SeatAssignment[],
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
    stateMocks.plannerState.seats = [{ id: "seat-1", x: 0, y: 0 }];
    stateMocks.plannerState.template = {
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [{ id: "seat-1", x: 0, y: 0 }],
      fixtures: [],
    };
    stateMocks.plannerState.seatAssignments = [];
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
    expect(wrapper.get("section").classes()).toContain("flex-1");
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

  it("renders symbolic markers for visible smart rules on occupied seats", () => {
    stateMocks.plannerState.seats = [
      { id: "seat-1", x: 0, y: 0 },
      { id: "seat-2", x: 120, y: 0 },
    ];
    stateMocks.plannerState.template = {
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: [
        { id: "seat-1", x: 0, y: 0 },
        { id: "seat-2", x: 120, y: 0 },
      ],
      fixtures: [],
    };
    stateMocks.plannerState.studentBySeatId = {
      "seat-1": { id: "student-1", display_name: "Ada" },
      "seat-2": { id: "student-2", display_name: "Alan" },
    };
    stateMocks.plannerState.seatAssignments = [
      { student_id: "student-1", seat_id: "seat-1" },
      { student_id: "student-2", seat_id: "seat-2" },
    ];

    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        selectedStudentIds: ["student-1"],
        relationshipRules: [
          { id: "near-1", kind: "keep_near", student_ids: ["student-1", "student-2"] },
        ],
        seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
        surfaceScale: 1,
      },
    });

    expect(wrapper.find('[data-test="seat-rule-marker-seat-1-near-teacher-neutral"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="seat-rule-marker-seat-1-keep-near-neutral"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="seat-markers-seat-1"]').classes()).toContain("flex-col-reverse");
  });

  it("does not infer near-teacher fulfillment tone on the seating map", () => {
    const seats = [
      { id: "seat-top-left", x: 0, y: 0 },
      { id: "seat-top-right", x: 120, y: 0 },
      { id: "seat-mid-left", x: 0, y: 120 },
      { id: "seat-mid-right", x: 120, y: 120 },
      { id: "seat-bottom-left", x: 0, y: 240 },
      { id: "seat-bottom-right", x: 120, y: 240 },
    ];
    stateMocks.plannerState.seats = seats;
    stateMocks.plannerState.template = {
      id: "template-bottom-anchor",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats,
      fixtures: [
        { id: "whiteboard-bottom", type: "whiteboard", x: 0, y: 336, width: 240, height: 48 },
      ],
    };
    stateMocks.plannerState.studentBySeatId = {
      "seat-top-left": { id: "student-1", display_name: "Ada" },
      "seat-top-right": null,
      "seat-mid-left": null,
      "seat-mid-right": null,
      "seat-bottom-left": null,
      "seat-bottom-right": null,
    };
    stateMocks.plannerState.seatAssignments = [
      { student_id: "student-1", seat_id: "seat-top-left" },
    ];

    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
        surfaceScale: 1,
      },
    });

    expect(wrapper.find('[data-test="seat-rule-marker-seat-top-left-near-teacher-neutral"]').exists())
      .toBe(true);
    expect(wrapper.find('[data-test="seat-rule-marker-seat-top-left-near-teacher-warning"]').exists())
      .toBe(false);
  });

  it("uses solver diagnostics for soft-rule marker tones when assignments still match", () => {
    stateMocks.plannerState.seats = [
      { id: "seat-1", x: 0, y: 0 },
      { id: "seat-2", x: 120, y: 0 },
    ];
    stateMocks.plannerState.template = {
      id: "template-1",
      name: "Sal 101",
      grid_cols: 14,
      grid_rows: 9,
      seats: stateMocks.plannerState.seats,
      fixtures: [],
    };
    stateMocks.plannerState.studentBySeatId = {
      "seat-1": { id: "student-1", display_name: "Ada" },
      "seat-2": { id: "student-2", display_name: "Alan" },
    };
    stateMocks.plannerState.seatAssignments = [
      { student_id: "student-1", seat_id: "seat-1" },
      { student_id: "student-2", seat_id: "seat-2" },
    ];

    const wrapper = mount(RoomCanvas, {
      props: {
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        relationshipRules: [
          { id: "near-1", kind: "keep_near", student_ids: ["student-1", "student-2"] },
        ],
        seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
        ruleDiagnostics: [
          {
            rule_id: "near_teacher:student-1",
            rule_kind: "near_teacher",
            status: "degraded",
            student_ids: ["student-1"],
            seat_ids: ["seat-1"],
            reason_code: "near_teacher_row_front_compromise",
            freshness_key: "fresh-near-teacher",
          },
          {
            rule_id: "near-1",
            rule_kind: "keep_near",
            status: "failed",
            student_ids: ["student-1", "student-2"],
            seat_ids: ["seat-1", "seat-2"],
            reason_code: "keep_near_not_close",
            freshness_key: "fresh-keep-near",
          },
        ],
        surfaceScale: 1,
      },
    });

    expect(wrapper.find('[data-test="seat-rule-marker-seat-1-near-teacher-warning"]').exists())
      .toBe(true);
    expect(wrapper.find('[data-test="seat-rule-marker-seat-1-keep-near-error"]').exists())
      .toBe(true);
  });

  it("renders a success fixed-seat symbol when the fixed student occupies the fixed seat", () => {
    stateMocks.plannerState.studentBySeatId = {
      "seat-1": { id: "student-1", display_name: "Ada" },
    };
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-1", seat_id: "seat-1" }];

    const wrapper = mount(RoomCanvas, {
      props: {
        fixedSeatRules: [
          { id: "fixed-1", template_id: "template-1", student_id: "student-1", seat_id: "seat-1" },
        ],
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        surfaceScale: 1,
      },
    });

    expect(wrapper.get('[data-test="seat-rule-marker-seat-1-fixed-seat-success"]').attributes("title")).toBe(
      "Ada ska sitta på plats-1. Regeln är uppfylld.",
    );
    expect(wrapper.get('[data-test="seat-rule-marker-seat-1-fixed-seat-success"]').html())
      .toContain("lucide-lock-keyhole");
  });

  it("renders an error fixed-seat symbol for the wrong occupant", () => {
    stateMocks.plannerState.studentBySeatId = {
      "seat-1": { id: "student-2", display_name: "Alan" },
    };
    stateMocks.plannerState.seatAssignments = [{ student_id: "student-2", seat_id: "seat-1" }];

    const wrapper = mount(RoomCanvas, {
      props: {
        fixedSeatRules: [
          { id: "fixed-1", template_id: "template-1", student_id: "student-1", seat_id: "seat-1" },
        ],
        scalePercent: 100,
        scaledSurfaceStyle: { width: "1400px", height: "960px" },
        surfaceScale: 1,
      },
    });

    expect(wrapper.get('[data-test="seat-rule-marker-seat-1-fixed-seat-error"]').attributes("title")).toBe(
      "Ada ska sitta på plats-1. Nu sitter Alan där.",
    );
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
    expect(wrapper.get('[data-test="room-canvas-scroll-frame"]').attributes("style")).toBeUndefined();
    expect(wrapper.get('[data-test="room-canvas-surface-shell"]').classes()).toContain("px-6");
    expect(wrapper.get('[data-test="room-canvas-surface-shell"]').classes()).toContain("py-6");
  });
});
