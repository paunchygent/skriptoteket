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
    expect(wrapper.get('[data-test="rules-map-view-planning"]').text()).toContain("Planeringsvy");
    expect(wrapper.get('[data-test="rules-map-view-seating"]').text()).toContain("Klassrumsvy");
    expect(wrapper.get('[data-test="rules-map-view-planning"]').attributes("style")).toContain(
      "min-width:",
    );
    expect(wrapper.get('[data-test="rules-map-view-seating"]').attributes("style")).toContain(
      "min-width:",
    );
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
