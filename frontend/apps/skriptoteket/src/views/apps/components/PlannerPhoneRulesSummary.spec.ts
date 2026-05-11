/**
 * Phone active rules summary tests.
 *
 * Purpose:
 *   Prove the reduced phone rules management surface exposes persisted rule
 *   edit/delete actions without owning persistence state.
 *
 * Relationships:
 *   - covers `PlannerPhoneRulesSummary.vue`
 *   - complements `PlannerRulesWorkspacePane` integration tests
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerPhoneRulesSummary from "./PlannerPhoneRulesSummary.vue";
import type { FixedSeatRule, RelationshipRule, Student } from "../classroomPlannerTypes";

const studentsById: Record<string, Student> = {
  "student-1": { id: "student-1", display_name: "Ada Lovelace" },
  "student-2": { id: "student-2", display_name: "Alan Turing" },
  "student-3": { id: "student-3", display_name: "Grace Hopper" },
  "student-4": { id: "student-4", display_name: "Nora Johansson" },
};

const relationshipRules: RelationshipRule[] = [
  { id: "rule-apart", kind: "keep_apart", student_ids: ["student-2", "student-3"] },
  { id: "rule-near", kind: "keep_near", student_ids: ["student-1", "student-4"] },
];

const fixedSeatRules: FixedSeatRule[] = [
  {
    id: "fixed-1",
    template_id: "template-1",
    student_id: "student-4",
    seat_id: "seat-12",
  },
];

describe("PlannerPhoneRulesSummary", () => {
  it("does not render an empty management panel when no persisted rules exist", () => {
    const wrapper = mount(PlannerPhoneRulesSummary, {
      props: {
        canEdit: true,
        studentsById,
      },
    });

    expect(wrapper.find('[data-test="phone-rules-active-summary"]').exists()).toBe(false);
  });

  it("renders compact persisted-rule rows with a count", () => {
    const wrapper = mount(PlannerPhoneRulesSummary, {
      props: {
        canEdit: true,
        nearTeacherStudents: [studentsById["student-1"], studentsById["student-2"]],
        relationshipRules,
        fixedSeatRules,
        studentsById,
      },
    });

    expect(wrapper.get('[data-test="phone-rules-active-count"]').text()).toBe("4");
    expect(wrapper.get('[data-test="phone-rules-active-row-fixed-seat"]').text()).toContain(
      "Nora Johansson",
    );
    expect(wrapper.get('[data-test="phone-rules-active-row-near-teacher"]').text()).toContain(
      "Ada Lovelace",
    );
    expect(wrapper.findAll('[data-test="phone-rules-active-row-relationship"]')).toHaveLength(2);
    expect(wrapper.text()).toContain("Håll isär");
    expect(wrapper.text()).toContain("Håll nära");
  });

  it("emits desktop-aligned edit and delete events for each rule family", async () => {
    const wrapper = mount(PlannerPhoneRulesSummary, {
      props: {
        canEdit: true,
        nearTeacherStudents: [studentsById["student-1"]],
        relationshipRules,
        fixedSeatRules,
        studentsById,
      },
    });

    await wrapper.get('[data-test="phone-rules-edit-near-teacher"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-delete-near-teacher"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-edit-rule-0"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-delete-rule-1"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-edit-fixed-seat-fixed-1"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-delete-fixed-seat-fixed-1"]').trigger("click");

    expect(wrapper.emitted("edit-near-teacher")).toHaveLength(1);
    expect(wrapper.emitted("delete-near-teacher")).toHaveLength(1);
    expect(wrapper.emitted("edit-rule")).toEqual([["rule-apart"]]);
    expect(wrapper.emitted("delete-rule")).toEqual([["rule-near"]]);
    expect(wrapper.emitted("edit-fixed-seat-rule")).toEqual([["fixed-1"]]);
    expect(wrapper.emitted("delete-fixed-seat-rule")).toEqual([["fixed-1"]]);
  });

  it("keeps management actions disabled when smart rules cannot be edited", () => {
    const wrapper = mount(PlannerPhoneRulesSummary, {
      props: {
        canEdit: false,
        nearTeacherStudents: [studentsById["student-1"]],
        relationshipRules,
        fixedSeatRules,
        studentsById,
      },
    });

    expect(wrapper.get('[data-test="phone-rules-edit-near-teacher"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="phone-rules-delete-rule-0"]').attributes("disabled")).toBeDefined();
    expect(wrapper.get('[data-test="phone-rules-delete-fixed-seat-fixed-1"]').attributes("disabled")).toBeDefined();
  });
});
