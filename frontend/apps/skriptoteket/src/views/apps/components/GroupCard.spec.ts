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
      },
    });

    const studentLabels = wrapper.findAll('[data-test="group-student-name"]');
    const firstStudentRow = wrapper.get('[data-test="group-student-row-student-1"]');

    expect(studentLabels).toHaveLength(8);
    expect(wrapper.get('[data-test="group-card"]').classes()).toContain("planner-group-card");
    expect(wrapper.get('[data-test="group-card"]').classes()).not.toContain("h-[234px]");
    expect(wrapper.get('[data-test="group-card"]').classes()).not.toContain("max-h-[234px]");
    expect(wrapper.get('[data-test="group-card"]').classes()).not.toContain("overflow-y-auto");
    expect(firstStudentRow.classes()).toContain("min-h-[56px]");
    expect(wrapper.get('[data-test="group-card-body"]').classes()).toContain("flex-1");
    expect(wrapper.get('[data-test="group-card-body"]').classes()).toContain("min-h-0");
    expect(wrapper.get('[data-test="group-card-body"]').classes()).not.toContain("overflow-y-auto");
    for (const label of studentLabels) {
      expect(label.classes()).toContain("break-words");
      expect(label.classes()).not.toContain("truncate");
    }
  });

  it("uses the approved taller empty-state and assigned-row floors", () => {
    const wrapper = mount(GroupCard, {
      props: {
        group: {
          id: "group-a",
          name: "Grupp A",
          sort_order: 0,
          name_is_custom: false,
        },
        students: [],
        canMoveUp: false,
        canMoveDown: true,
      },
    });

    expect(wrapper.get('[data-test="group-empty-drop-zone"]').classes()).toContain("min-h-[112px]");
    expect(wrapper.get('[data-test="group-empty-drop-zone"]').classes()).toContain("flex-1");
    expect(wrapper.get('[data-test="group-card"]').classes()).toContain("planner-group-card");
  });

  it("keeps the desktop card floor even after one student is assigned", () => {
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
      },
    });

    expect(wrapper.get('[data-test="group-card"]').classes()).toContain("planner-group-card");
    expect(wrapper.get('[data-test="group-card"]').classes()).not.toContain("max-h-[234px]");
    expect(wrapper.find('[data-test="group-empty-drop-zone"]').exists()).toBe(false);
  });

  it("keeps assigned student rows hover-only without a persistent selected hue", () => {
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
      },
    });

    const row = wrapper.get('[data-test="group-student-row-student-1"]');

    expect(row.classes()).toContain("border-navy");
    expect(row.classes()).toContain("bg-white");
    expect(row.classes()).toContain("hover:bg-canvas");
    expect(row.classes()).not.toContain("border-burgundy");
    expect(row.classes()).not.toContain("bg-burgundy/10");
    expect(row.classes()).not.toContain("text-burgundy");
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
