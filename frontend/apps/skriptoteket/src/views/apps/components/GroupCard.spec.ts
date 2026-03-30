import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import GroupCard from "./GroupCard.vue";

function buildStudents(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    id: `student-${index + 1}`,
    display_name: `Elev ${index + 1} med ett ovanligt langt namn som maste kunna radbrytas`,
  }));
}

describe("GroupCard", () => {
  it("keeps the rename row compact without a redundant group-name label", () => {
    const wrapper = mount(GroupCard, {
      props: {
        group: {
          id: "group-a",
          name: "Grupp 1",
          sort_order: 0,
          name_is_custom: false,
        },
        students: [],
        canMoveUp: false,
        canMoveDown: true,
        selectedStudentId: null,
      },
    });

    expect(wrapper.text()).not.toContain("Gruppnamn");
    expect(wrapper.get('[data-test="group-name-input"]').classes()).toContain("h-[36px]");
    expect(wrapper.get('[data-test="move-group-up"]').classes()).toContain("planner-btn-icon-lg");
    expect(wrapper.get('[data-test="move-group-down"]').classes()).toContain("planner-btn-icon-lg");
    expect(wrapper.get('[data-test="remove-group"]').classes()).toContain("planner-btn-icon-lg");
  });

  it("does not emit a rename on blur when the visible name is unchanged", async () => {
    const wrapper = mount(GroupCard, {
      props: {
        group: {
          id: "group-a",
          name: "Grupp 1",
          sort_order: 0,
          name_is_custom: false,
        },
        students: [],
        canMoveUp: false,
        canMoveDown: true,
        selectedStudentId: null,
      },
    });

    await wrapper.get('input[type="text"]').trigger("blur");

    expect(wrapper.emitted("group-renamed")).toBeUndefined();
  });

  it("shows meaningful order state and emits reorder offsets", async () => {
    const wrapper = mount(GroupCard, {
      props: {
        group: {
          id: "group-b",
          name: "Handledargrupp",
          sort_order: 2,
          name_is_custom: true,
        },
        students: buildStudents(2),
        canMoveUp: true,
        canMoveDown: false,
        selectedStudentId: null,
      },
    });

    expect(wrapper.get('[data-test="move-group-up"]').attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-test="move-group-down"]').attributes("disabled")).toBeDefined();

    await wrapper.get('[data-test="move-group-up"]').trigger("click");

    expect(wrapper.emitted("group-moved")).toEqual([["group-b", -1]]);
  });

  it("renders larger groups with wrapping student labels and growth-friendly card structure", () => {
    const wrapper = mount(GroupCard, {
      props: {
        group: {
          id: "group-a",
          name: "Grupp A",
          sort_order: 0,
          name_is_custom: false,
        },
        students: buildStudents(8),
        canMoveUp: false,
        canMoveDown: true,
        selectedStudentId: null,
      },
    });

    const studentLabels = wrapper.findAll('[data-test="group-student-name"]');

    expect(studentLabels).toHaveLength(8);
    expect(wrapper.get('[data-test="group-card"]').classes()).toContain("self-start");
    for (const label of studentLabels) {
      expect(label.classes()).toContain("break-words");
      expect(label.classes()).not.toContain("truncate");
    }
  });

  it("shows smart-rule markers on assigned student bars", () => {
    const wrapper = mount(GroupCard, {
      props: {
        group: {
          id: "group-a",
          name: "Grupp A",
          sort_order: 0,
          name_is_custom: false,
        },
        students: [{ id: "student-1", display_name: "Ada Lovelace" }],
        canMoveUp: false,
        canMoveDown: true,
        selectedStudentId: null,
        smartRuleMarkersByStudentId: {
          "student-1": ["Nära läraren", "Isär A"],
        },
      },
    });

    expect(wrapper.get('[data-test="group-student-markers-student-1"]').text()).toContain(
      "Nära läraren",
    );
    expect(wrapper.get('[data-test="group-student-markers-student-1"]').text()).toContain("Isär A");
  });
});
