/**
 * Rules map canvas tests.
 *
 * These tests lock the map-surface contract for `Regler`, especially the
 * no-classroom branch where the default planning view still needs to show the
 * approved guidance copy and an actionable off-map roster.
 */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerRulesMapCanvas from "./PlannerRulesMapCanvas.vue";

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

describe("PlannerRulesMapCanvas", () => {
  const template = {
    id: "template-1",
    name: "Sal 101",
    seats: [
      { id: "seat-1", x: 0, y: 0, width: 1, height: 1, label: "1", zone: null },
    ],
    fixtures: [],
  };

  const students = [
    { id: "student-1", display_name: "Ada Lovelace" },
    { id: "student-2", display_name: "Alan Turing" },
  ];

  beforeEach(() => {
    vi.stubGlobal("ResizeObserver", ResizeObserverMock);
    setViewportSize(1200, 800);
  });

  it("keeps Planeringskarta as an abstract alphabetical roster even when a template exists", () => {
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "planning_map",
        rosterName: "SR24D",
        template,
        students,
        studentsById: { "student-1": students[0], "student-2": students[1] },
        pendingSelectedStudentIds: ["student-2"],
        seatAssignments: [],
      },
      global: {
        stubs: {
          RoomSceneSurface: {
            template: "<div data-test='room-scene-surface'><slot name='floor-overlay' /></div>",
          },
          PlannerRulesSeatNode: {
            template: "<button data-test='rules-seat-node' />",
          },
        },
      },
    });

    expect(wrapper.find('[data-test="rules-map-empty-state"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="rules-map-canvas"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="rules-map-surface-heading"]').text()).toBe("SR24D");
    expect(wrapper.get('[data-test="rules-map-unplaced-count"]').text()).toContain("2 elever");
    expect(wrapper.findAll('button[data-test^="rules-unplaced-student-"]')).toHaveLength(2);
    expect(wrapper.get('[data-test="rules-map-view-planning"]').text()).toContain("Planeringskarta");
    expect(wrapper.get('[data-test="rules-map-view-seating"]').text()).toContain("Klassrumsvy");
    expect(wrapper.get('[data-test="rules-map-view-planning"]').attributes("style")).toContain(
      "min-width:",
    );
    expect(wrapper.get('[data-test="rules-map-view-seating"]').attributes("style")).toContain(
      "min-width:",
    );
    expect(wrapper.findAll('[data-ui-option="segmented-toggle-option"] button').map((button) =>
      button.text(),
    )).toEqual(["Klassrumsvy", "Planeringskarta"]);
    expect(wrapper.get('[data-test="rules-unplaced-student-student-1"]').text()).toContain(
      "Ada Lovelace",
    );
    expect(wrapper.get('[data-test="rules-unplaced-student-student-2"]').text()).toContain(
      "Alan Turing",
    );
    expect(wrapper.get('[data-test="rules-map-unplaced-selected-count"]').text()).toContain(
      "1 valda",
    );
    expect(wrapper.get('[data-test="rules-unplaced-student-order-student-2"]').text()).toBe("1");
    expect(wrapper.get('[data-test="rules-zoom-out"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="rules-zoom-in"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="rules-zoom-fit"]').attributes("disabled")).toBeDefined();
  });

  it("switches to the seating canvas when Sittschema is active", async () => {
    setViewportSize(800, 600);

    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "planning_map",
        rosterName: "SR24D",
        template,
        students,
        studentsById: { "student-1": students[0], "student-2": students[1] },
        seatAssignments: [],
      },
      global: {
        stubs: {
          RoomSceneSurface: {
            template: "<div data-test='room-scene-surface'><slot name='floor-overlay' /></div>",
          },
          PlannerRulesSeatNode: {
            template: "<button data-test='rules-seat-node' />",
          },
        },
      },
    });

    await wrapper.setProps({
      mapView: "seating_arrangement",
      seatAssignments: [{ seat_id: "seat-1", student_id: "student-1" }],
      canShowSeatingArrangement: true,
    });
    await nextTick();
    await nextTick();

    expect(wrapper.find('[data-test="rules-map-canvas"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="rules-map-empty-state"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-test="rules-seat-node"]')).toHaveLength(1);
    expect(Number.parseInt(wrapper.get('[data-test="rules-zoom-percent"]').text(), 10)).not.toBe(100);
    expect(wrapper.get('[data-test="rules-map-scroll-frame"]').attributes("data-overflow-anchor")).toBe(
      "center",
    );
    expect(wrapper.get('[data-test="rules-map-scroll-frame"]').attributes("style")).toBeUndefined();
    expect(wrapper.get('[data-test="rules-map-surface-shell"]').classes()).toContain("px-6");
    expect(wrapper.get('[data-test="rules-map-surface-shell"]').classes()).toContain("py-6");
  });

  it("emits fixed-seat selections and renders saved lock markers", async () => {
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "seating_arrangement",
        rosterName: "SR24D",
        template: {
          ...template,
          seats: [
            { id: "seat-1", x: 0, y: 0, zone: null },
            { id: "seat-2", x: 120, y: 0, zone: null },
          ],
        },
        students,
        studentsById: { "student-1": students[0], "student-2": students[1] },
        seatAssignments: [{ seat_id: "seat-1", student_id: "student-1" }],
        activeTool: "fixed_seat",
        pendingFixedSeatStudentId: "student-2",
        pendingFixedSeatSeatId: "seat-2",
        fixedSeatRules: [
          {
            id: "fixed-1",
            template_id: "template-1",
            student_id: "student-1",
            seat_id: "seat-1",
          },
        ],
      },
      global: {
        stubs: {
          RoomSceneSurface: {
            template: "<div data-test='room-scene-surface'><slot name='floor-overlay' /></div>",
          },
        },
      },
    });

    expect(wrapper.get('[data-test="rules-seat-rule-marker-seat-1-fixed-seat-success"]').attributes("title"))
      .toContain(
        "Ada Lovelace ska sitta på plats-1. Regeln är uppfylld.",
    );
    expect(wrapper.get('[data-test="rules-seat-rule-marker-seat-2-fixed-seat-warning"]').attributes("title"))
      .toContain(
        "Vald plats för Alan Turing.",
    );
    expect(wrapper.find('[data-test="rules-seat-pending-label-seat-2"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="rules-unplaced-student-student-2"]').attributes("aria-pressed"))
      .toBe("true");
    expect(wrapper.get('[data-test="rules-unplaced-fixed-seat-preview-student-2"]').text()).toBe(
      "Fast plats",
    );

    await wrapper.get('[data-test="rules-seat-node-seat-2"] button').trigger("click");

    expect(wrapper.emitted("seat-selected")).toEqual([["seat-2"]]);
  });

  it("renders global symbolic rule markers on classroom-map seats", () => {
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "seating_arrangement",
        rosterName: "SR24D",
        template: {
          ...template,
          seats: [
            { id: "seat-1", x: 0, y: 0, zone: null },
            { id: "seat-2", x: 120, y: 0, zone: null },
          ],
        },
        students,
        studentsById: { "student-1": students[0], "student-2": students[1] },
        seatAssignments: [
          { seat_id: "seat-1", student_id: "student-1" },
          { seat_id: "seat-2", student_id: "student-2" },
        ],
        relationshipRules: [
          { id: "near-1", kind: "keep_near", student_ids: ["student-1", "student-2"] },
        ],
        seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
      },
      global: {
        stubs: {
          RoomSceneSurface: {
            template: "<div data-test='room-scene-surface'><slot name='floor-overlay' /></div>",
          },
        },
      },
    });

    expect(wrapper.find('[data-test="rules-seat-rule-marker-seat-1-keep-near-success"]').exists())
      .toBe(true);
    expect(wrapper.find('[data-test="rules-seat-rule-marker-seat-1-near-teacher-success"]').exists())
      .toBe(true);
  });

  it("uses the solver teaching anchor when toning near-teacher markers on the rules map", () => {
    const rightAnchorTemplate = {
      ...template,
      seats: [
        { id: "seat-left-top", x: 0, y: 0, zone: null },
        { id: "seat-left-bottom", x: 0, y: 120, zone: null },
        { id: "seat-mid-top", x: 120, y: 0, zone: null },
        { id: "seat-mid-bottom", x: 120, y: 120, zone: null },
        { id: "seat-right-top", x: 240, y: 0, zone: null },
        { id: "seat-right-bottom", x: 240, y: 120, zone: null },
      ],
      fixtures: [
        { id: "whiteboard-right", type: "whiteboard" as const, x: 336, y: 0, width: 48, height: 240 },
      ],
    };
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "seating_arrangement",
        rosterName: "SR24D",
        template: rightAnchorTemplate,
        students,
        studentsById: { "student-1": students[0], "student-2": students[1] },
        seatAssignments: [
          { seat_id: "seat-left-top", student_id: "student-1" },
        ],
        seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
      },
      global: {
        stubs: {
          RoomSceneSurface: {
            template: "<div data-test='room-scene-surface'><slot name='floor-overlay' /></div>",
          },
        },
      },
    });

    expect(wrapper.find('[data-test="rules-seat-rule-marker-seat-left-top-near-teacher-warning"]').exists())
      .toBe(true);
  });

  it("routes fixed-seat canvas clicks through physical-seat precedence", async () => {
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "seating_arrangement",
        rosterName: "SR24D",
        template: {
          ...template,
          seats: [
            { id: "seat-1", x: 0, y: 0, zone: null },
            { id: "seat-2", x: 120, y: 0, zone: null },
          ],
        },
        students,
        studentsById: { "student-1": students[0], "student-2": students[1] },
        seatAssignments: [{ seat_id: "seat-1", student_id: "student-1" }],
        activeTool: "fixed_seat",
        pendingFixedSeatStudentId: "student-1",
        pendingFixedSeatSeatId: null,
      },
      global: {
        stubs: {
          RoomSceneSurface: {
            template: "<div data-test='room-scene-surface'><slot name='floor-overlay' /></div>",
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-seat-node-seat-1"] button').trigger("click");

    expect(wrapper.emitted("seat-selected")).toEqual([["seat-1"]]);
    expect(wrapper.emitted("student-selected")).toBeUndefined();

    await wrapper.setProps({ pendingFixedSeatSeatId: "seat-2" });
    await wrapper.get('[data-test="rules-seat-node-seat-2"] button').trigger("click");

    expect(wrapper.emitted("seat-selected")).toEqual([["seat-1"], ["seat-2"]]);
  });

  it("shows the seating guidance only when Sittschema has no template to project", () => {
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "seating_arrangement",
        rosterName: "SR24D",
        template: null,
        students: [
          { id: "student-1", display_name: "Ada Lovelace" },
          { id: "student-2", display_name: "Alan Turing" },
        ],
        pendingSelectedStudentIds: ["student-2"],
      },
    });

    expect(wrapper.get('[data-test="rules-map-empty-state"]').text()).toContain(
      "Välj ett klassrum i arbetsytan Sittplatser och placera ut eleverna om du vill arbeta med regler direkt utifrån klassrummets möblering.",
    );
    expect(wrapper.get('[data-test="rules-map-surface-heading"]').text()).toBe("Ej på karta");
    expect(wrapper.get('[data-test="rules-map-unplaced-count"]').text()).toContain("2 elever");
    expect(wrapper.get('[data-test="rules-map-unplaced-selected-count"]').text()).toContain(
      "1 valda",
    );
    expect(wrapper.find('[data-test="rules-map-unplaced-grid"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="rules-unplaced-student-student-1"]').attributes("aria-pressed"))
      .toBe("false");
    expect(wrapper.get('[data-test="rules-unplaced-student-student-2"]').attributes("aria-pressed"))
      .toBe("true");
    expect(wrapper.get('[data-test="rules-unplaced-student-order-student-2"]').text()).toBe("1");
  });

  it("shows the no-classroom guidance in the default planning view and keeps the roster actionable", () => {
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "planning_map",
        rosterName: "SR24D",
        template: null,
        students: [
          { id: "student-1", display_name: "Ada Lovelace" },
          { id: "student-2", display_name: "Alan Turing" },
        ],
        pendingSelectedStudentIds: ["student-2"],
      },
    });

    expect(wrapper.get('[data-test="rules-map-empty-state"]').text()).toContain(
      "Välj ett klassrum i arbetsytan Sittplatser och placera ut eleverna om du vill arbeta med regler direkt utifrån klassrummets möblering.",
    );
    expect(wrapper.find('[data-test="rules-map-canvas"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="rules-map-surface-heading"]').text()).toBe("SR24D");
    expect(wrapper.get('[data-test="rules-map-unplaced-count"]').text()).toContain("2 elever");
    expect(wrapper.get('[data-test="rules-map-unplaced-selected-count"]').text()).toContain(
      "1 valda",
    );
    expect(wrapper.find('[data-test="rules-map-unplaced-grid"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="rules-unplaced-student-student-1"]').attributes("aria-pressed"))
      .toBe("false");
    expect(wrapper.get('[data-test="rules-unplaced-student-student-2"]').attributes("aria-pressed"))
      .toBe("true");
  });
});
