import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GroupBoard from "./GroupBoard.vue";

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    groups: [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }],
    isWorkspaceBusy: false,
    studentsByGroupId: {
      "group-a": [{ id: "student-2", display_name: "Bo" }],
    } as Record<string, Array<{ id: string; display_name: string }>>,
    assignStudentToGroup: vi.fn(),
    removeStudentFromGroup: vi.fn(),
    renameGroup: vi.fn(),
    moveGroup: vi.fn(),
    removeGroup: vi.fn(),
  },
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

function mountBoard() {
  return mount(GroupBoard, {
    props: {
      smartRuleMarkersByStudentId: {
        "student-2": ["Isär A"],
      },
    },
    global: {
      stubs: {
        GroupCard: {
          props: [
            "group",
            "students",
            "smartRuleMarkersByStudentId",
            "disabled",
            "canMoveUp",
            "canMoveDown",
          ],
          template: `
            <div
              data-test="group-card"
              :data-disabled="String(disabled)"
              :data-marker-count="String((smartRuleMarkersByStudentId?.['student-2'] ?? []).length)"
            >
              {{ group.name }} · {{ students.length }}
            </div>
          `,
        },
      },
    },
  });
}

describe("GroupBoard", () => {
  beforeEach(() => {
    stateMocks.plannerState.assignStudentToGroup.mockReset();
    stateMocks.plannerState.removeStudentFromGroup.mockReset();
    stateMocks.plannerState.renameGroup.mockReset();
    stateMocks.plannerState.moveGroup.mockReset();
    stateMocks.plannerState.removeGroup.mockReset();
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.groups = [{ id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false }];
    stateMocks.plannerState.studentsByGroupId = {
      "group-a": [{ id: "student-2", display_name: "Bo" }],
    } as Record<string, Array<{ id: string; display_name: string }>>;
  });

  it("does not leak seat labels into the grouping surface", () => {
    const wrapper = mountBoard();

    expect(wrapper.text()).toContain("Grupp A");
    expect(wrapper.text()).not.toContain("Plats");
    expect(wrapper.text()).not.toContain("seat-1");
    expect(wrapper.text()).not.toContain("seat-2");
  });

  it("renders ordered group cards without wiring a dead selected-student state", () => {
    stateMocks.plannerState.groups = [
      { id: "group-b", name: "Grupp B", sort_order: 1, name_is_custom: false },
      { id: "group-a", name: "Grupp A", sort_order: 0, name_is_custom: false },
    ];
    stateMocks.plannerState.studentsByGroupId = {
      "group-a": [{ id: "student-2", display_name: "Bo" }],
      "group-b": [{ id: "student-3", display_name: "Cleo" }],
    } as Record<string, Array<{ id: string; display_name: string }>>;

    const wrapper = mountBoard();
    const cards = wrapper.findAll('[data-test="group-card"]');

    expect(cards).toHaveLength(2);
    expect(cards[0]?.text()).toContain("Grupp A");
    expect(cards[1]?.text()).toContain("Grupp B");
  });

  it("passes the workspace busy state down to group cards", () => {
    stateMocks.plannerState.isWorkspaceBusy = true;

    const wrapper = mountBoard();

    expect(wrapper.get('[data-test="group-card"]').attributes("data-disabled")).toBe("true");
  });

  it("forwards smart-rule markers to the rendered group cards", () => {
    const wrapper = mountBoard();

    expect(wrapper.get('[data-test="group-card"]').attributes("data-marker-count")).toBe("1");
  });
});
