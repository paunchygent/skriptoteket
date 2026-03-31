import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerRulesMapCanvas from "./PlannerRulesMapCanvas.vue";

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
  ];

  it("keeps a keyed surface when switching between planning map and seating arrangement", async () => {
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "planning_map",
        template,
        students,
        studentsById: { "student-1": students[0] },
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

    expect(wrapper.find('[data-test="rules-map-canvas"]').exists()).toBe(true);

    await wrapper.setProps({
      mapView: "seating_arrangement",
      seatAssignments: [{ seat_id: "seat-1", student_id: "student-1" }],
      canShowSeatingArrangement: true,
    });

    expect(wrapper.find('[data-test="rules-map-canvas"]').exists()).toBe(true);
    expect(wrapper.findAll('[data-test="rules-seat-node"]')).toHaveLength(1);
  });

  it("uses the approved no-classroom copy and organized off-map roster when no template exists", () => {
    const wrapper = mount(PlannerRulesMapCanvas, {
      props: {
        mapView: "planning_map",
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
    expect(wrapper.get('[data-test="rules-map-unplaced"]').text()).toContain("Ej på karta");
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
});
