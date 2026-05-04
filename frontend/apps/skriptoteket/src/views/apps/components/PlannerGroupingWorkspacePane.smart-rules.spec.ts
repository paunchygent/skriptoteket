/**
 * Grouping workspace smart-rule visibility tests.
 *
 * These tests keep smart-rule markers visible on student bars both before and
 * after assignment so grouping can expose whether the current grouping still
 * respects the authored rules at a glance.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PlannerGroupingWorkspacePane from "./PlannerGroupingWorkspacePane.vue";
import type { DraftGroup, RelationshipRule, Roster } from "../classroomPlannerTypes";

type PlannerStateMock = {
  ungroupedStudents: Roster["students"];
  groups: DraftGroup[];
  studentsByGroupId: Record<string, Roster["students"]>;
  seatingPreferences: Array<{ student_id: string; near_teacher: boolean }>;
  relationshipRules: RelationshipRule[];
  smartRuleHydrationStatus: "idle" | "hydrating" | "ready" | "error";
  smartRuleHydrationMessage: string | null;
  isWorkspaceBusy: boolean;
  retrySmartRuleHydration: ReturnType<typeof vi.fn>;
  removeStudentFromGroup: ReturnType<typeof vi.fn>;
  assignStudentToGroup: ReturnType<typeof vi.fn>;
  renameGroup: ReturnType<typeof vi.fn>;
  moveGroup: ReturnType<typeof vi.fn>;
  removeGroup: ReturnType<typeof vi.fn>;
};

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    ungroupedStudents: [{ id: "student-2", display_name: "Alan Turing" }],
    groups: [{ id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
    studentsByGroupId: {
      "group-1": [{ id: "student-1", display_name: "Ada Lovelace" }],
    },
    seatingPreferences: [{ student_id: "student-1", near_teacher: true }],
    relationshipRules: [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ],
    smartRuleHydrationStatus: "ready",
    smartRuleHydrationMessage: null,
    isWorkspaceBusy: false,
    retrySmartRuleHydration: vi.fn(),
    removeStudentFromGroup: vi.fn(),
    assignStudentToGroup: vi.fn(),
    renameGroup: vi.fn(),
    moveGroup: vi.fn(),
    removeGroup: vi.fn(),
  }))(),
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerGroupingWorkspacePane smart-rule visibility", () => {
  beforeEach(() => {
    stateMocks.plannerState.ungroupedStudents = [{ id: "student-2", display_name: "Alan Turing" }];
    stateMocks.plannerState.groups = [
      { id: "group-1", name: "Grupp 1", sort_order: 0, name_is_custom: false },
    ];
    stateMocks.plannerState.studentsByGroupId = {
      "group-1": [{ id: "student-1", display_name: "Ada Lovelace" }],
    };
    stateMocks.plannerState.seatingPreferences = [{ student_id: "student-1", near_teacher: true }];
    stateMocks.plannerState.relationshipRules = [
      { id: "rule-1", kind: "keep_apart", student_ids: ["student-1", "student-2"] },
    ];
    stateMocks.plannerState.smartRuleHydrationStatus = "ready";
    stateMocks.plannerState.smartRuleHydrationMessage = null;
    stateMocks.plannerState.isWorkspaceBusy = false;
    stateMocks.plannerState.retrySmartRuleHydration.mockReset();
    stateMocks.plannerState.removeStudentFromGroup.mockReset();
    stateMocks.plannerState.assignStudentToGroup.mockReset();
    stateMocks.plannerState.renameGroup.mockReset();
    stateMocks.plannerState.moveGroup.mockReset();
    stateMocks.plannerState.removeGroup.mockReset();
  });

  it("keeps rule markers visible in the ungrouped pool and inside assigned group cards", () => {
    const wrapper = mount(PlannerGroupingWorkspacePane);

    expect(wrapper.get('[data-test="student-pool-markers-student-2"]').text()).toContain("Isär A");
    expect(wrapper.get('[data-test="group-student-markers-student-1"]').text()).toContain(
      "Nära läraren",
    );
    expect(wrapper.get('[data-test="group-student-markers-student-1"]').text()).toContain(
      "Isär A",
    );
  });

  it("keeps the ungrouped pool and board in a bounded desktop split workspace", () => {
    const wrapper = mount(PlannerGroupingWorkspacePane);
    const layoutRow = wrapper.get('[data-test="grouping-layout-lane"]');
    const pool = wrapper.get('[data-test="grouping-student-pool"]');
    const poolLane = wrapper.get('[data-test="grouping-student-pool-lane"]');
    const boardLane = wrapper.get('[data-test="grouping-board-lane"]');
    const scrollBody = wrapper.get('[data-test="grouping-student-pool-scroll-body"]');

    expect(layoutRow.classes()).toEqual(
      expect.arrayContaining([
        "planner-grouping-layout-row",
      ]),
    );
    expect(pool.classes()).toEqual(
      expect.arrayContaining([
        "planner-student-pool-surface",
      ]),
    );
    expect(pool.attributes("style")).toBeUndefined();
    expect(poolLane.classes()).toEqual(
      expect.arrayContaining([
        "planner-workspace-pool-lane",
        "planner-grouping-pool-lane",
      ]),
    );
    expect(boardLane.classes()).toEqual(
      expect.arrayContaining([
        "planner-workspace-primary-lane",
        "planner-grouping-board-lane",
      ]),
    );
    expect(scrollBody.classes()).toEqual(
      expect.arrayContaining([
        "min-h-0",
        "flex-1",
        "overflow-y-auto",
      ]),
    );
  });

  it("keeps unassigned students visible while selecting phone group targets", async () => {
    const wrapper = mount(PlannerGroupingWorkspacePane);

    expect(wrapper.find('[data-test="phone-grouping-student-pool"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="phone-grouping-active-card"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="phone-grouping-tab-group-1"]').classes()).toContain(
      "planner-phone-tab-active",
    );
    expect(wrapper.get('[data-test="phone-grouping-student-pool-scroll-body"]').classes()).toEqual(
      expect.arrayContaining([
        "min-h-0",
        "flex-1",
        "overflow-y-auto",
      ]),
    );

    await wrapper.get('[data-test="phone-grouping-tab-group-1"]').trigger("click");

    expect(wrapper.find('[data-test="phone-grouping-student-pool"]').exists()).toBe(true);
    expect(wrapper.get('[data-test="phone-grouping-active-card"]').text()).toContain("Ada Lovelace");
  });

  it("keeps a stable phone group target while groups are temporarily unavailable", async () => {
    stateMocks.plannerState.groups = [];
    stateMocks.plannerState.studentsByGroupId = {};

    const wrapper = mount(PlannerGroupingWorkspacePane);

    expect(wrapper.find('[data-test="phone-grouping-active-card"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="phone-grouping-target-placeholder"]').exists()).toBe(true);

    wrapper.unmount();

    stateMocks.plannerState.groups = [
      { id: "group-2", name: "Grupp 2", sort_order: 0, name_is_custom: false },
    ];
    stateMocks.plannerState.studentsByGroupId = {
      "group-2": [{ id: "student-2", display_name: "Alan Turing" }],
    };
    const reloadedWrapper = mount(PlannerGroupingWorkspacePane);

    expect(reloadedWrapper.find('[data-test="phone-grouping-target-placeholder"]').exists()).toBe(false);
    expect(reloadedWrapper.get('[data-test="phone-grouping-active-card"]').text()).toContain("Alan Turing");
    expect(reloadedWrapper.get('[data-test="phone-grouping-tab-group-2"]').classes()).toContain(
      "planner-phone-tab-active",
    );
  });
});
