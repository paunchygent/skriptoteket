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

    expect(wrapper.get('[data-test="group-order-badge"]').text()).toContain("Ordning 3");
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
});
