/**
 * Phone fixed-seat rule panel tests.
 *
 * These tests lock the phone map affordance so it keeps classroom-derived seat
 * geometry while using the existing fixed-seat selection event path.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerPhoneFixedSeatRulePanel from "./PlannerPhoneFixedSeatRulePanel.vue";

const template = {
  id: "template-1",
  name: "G20",
  grid_cols: 14,
  grid_rows: 9,
  fixtures: [
    { id: "fixture-1", type: "whiteboard" as const, x: 96, y: 0, width: 288, height: 96 },
    { id: "fixture-2", type: "teacher_desk" as const, x: 480, y: 96, width: 192, height: 96 },
  ],
  seats: [
    { id: "seat-1", x: 0, y: 192, zone: null },
    { id: "seat-12", x: 480, y: 384, zone: null },
  ],
};

describe("PlannerPhoneFixedSeatRulePanel", () => {
  it("renders a compact classroom map from template geometry and emits seat selection", async () => {
    const wrapper = mount(PlannerPhoneFixedSeatRulePanel, {
      props: {
        template,
        studentsById: {
          "student-1": { id: "student-1", display_name: "Vilma Ossner" },
        },
        pendingFixedSeatStudentId: "student-1",
        pendingFixedSeatSeatId: "seat-12",
      },
    });

    expect(wrapper.get('[data-test="phone-fixed-seat-pending-student"]').text()).toContain("Vilma Ossner");
    expect(wrapper.get('[data-test="phone-fixed-seat-pending-seat"]').text()).toContain("plats-12");
    expect(wrapper.get('[data-test="phone-fixed-seat-map-count"]').text()).toBe("2");
    expect(wrapper.find('[data-test="phone-fixed-seat-map"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="phone-fixed-seat-map"] > div:last-child').attributes("style")).toContain(
      "repeat(14, var(--planner-phone-seat-cell-size))",
    );
    expect(wrapper.get(".planner-phone-fixed-seat-map-fixture-whiteboard").classes()).toContain(
      "planner-phone-fixed-seat-map-fixture-wall-top",
    );
    expect(wrapper.get(".planner-phone-fixed-seat-map-fixture-whiteboard").text()).toBe("");
    expect(wrapper.get(".planner-phone-fixed-seat-map-fixture-whiteboard").attributes("aria-label")).toBe("Tavla");
    expect(wrapper.get('[data-test="phone-fixed-seat-map-seat-wrapper-seat-1"]').attributes("style")).toContain(
      "grid-row: 3 / span 1",
    );
    expect(wrapper.get('[data-test="phone-fixed-seat-map-seat-wrapper-seat-12"]').attributes("style")).toContain(
      "grid-column: 6 / span 1",
    );
    expect(wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-12"]').attributes("aria-pressed"))
      .toBe("true");

    await wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]').trigger("click");

    expect(wrapper.emitted("seat-selected")).toEqual([["seat-1"]]);
  });

  it("shows the classroom recovery copy instead of an empty map", () => {
    const wrapper = mount(PlannerPhoneFixedSeatRulePanel, {
      props: {
        template: null,
      },
    });

    expect(wrapper.find('[data-test="phone-fixed-seat-map"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="phone-fixed-seat-empty"]').text()).toContain(
      "Fast plats kräver ett klassrum.",
    );
  });

  it("renders compact symbolic rule markers without replacing the student seat label", () => {
    const wrapper = mount(PlannerPhoneFixedSeatRulePanel, {
      props: {
        template,
        studentsById: {
          "student-1": { id: "student-1", display_name: "Vilma Ossner" },
          "student-2": { id: "student-2", display_name: "Nora Johansson" },
        },
        seatAssignments: [
          { student_id: "student-1", seat_id: "seat-1" },
          { student_id: "student-2", seat_id: "seat-12" },
        ],
        fixedSeatRules: [
          { id: "fixed-1", template_id: "template-1", student_id: "student-1", seat_id: "seat-1" },
        ],
        relationshipRules: [
          { id: "apart-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
        ],
        seatingPreferences: [
          { student_id: "student-1", near_teacher: true },
        ],
      },
    });

    const seat = wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]');

    expect(seat.text()).toContain("Vilma");
    expect(wrapper.get('[data-test="phone-fixed-seat-map-seat-first-name-seat-1"]').text()).toBe("Vilma");
    expect(wrapper.get('[data-test="phone-fixed-seat-map-seat-last-initials-seat-1"]').text()).toBe("O");
    expect(wrapper.get('[data-test="phone-fixed-seat-map-seat-first-name-seat-12"]').text()).toBe("Nora");
    expect(wrapper.get('[data-test="phone-fixed-seat-map-seat-last-initials-seat-12"]').text()).toBe("J");
    expect(wrapper.find('[data-test="phone-seat-rule-marker-seat-1-fixed-seat-success"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="phone-seat-rule-marker-seat-1-keep-apart-success"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="phone-seat-rule-marker-seat-1-near-teacher-success"]').exists()).toBe(true);
  });

  it("uses the solver teaching anchor when toning near-teacher markers on the phone map", () => {
    const rightAnchorTemplate = {
      ...template,
      fixtures: [
        { id: "whiteboard-right", type: "whiteboard" as const, x: 1344, y: 0, width: 48, height: 864 },
      ],
      seats: [
        { id: "seat-left", x: 0, y: 0, zone: null },
        { id: "seat-middle", x: 480, y: 0, zone: null },
        { id: "seat-right", x: 960, y: 0, zone: null },
      ],
    };
    const wrapper = mount(PlannerPhoneFixedSeatRulePanel, {
      props: {
        template: rightAnchorTemplate,
        studentsById: {
          "student-1": { id: "student-1", display_name: "Vilma Ossner" },
        },
        seatAssignments: [
          { student_id: "student-1", seat_id: "seat-right" },
        ],
        seatingPreferences: [
          { student_id: "student-1", near_teacher: true },
        ],
      },
    });

    expect(wrapper.find('[data-test="phone-seat-rule-marker-seat-right-near-teacher-success"]').exists())
      .toBe(true);
  });
});
