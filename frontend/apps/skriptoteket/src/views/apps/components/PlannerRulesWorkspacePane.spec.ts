/**
 * Rules workspace pane tests.
 *
 * These tests lock the dedicated `Regler` workspace behavior so the map view
 * and top summary panel stay authoritative for smart-rule authoring after the
 * cut-over.
 *
 * This workflow covers relationship and near-teacher rule tools and their inspector.
 */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { resetPlannerState, stateMocks } from "./PlannerRulesWorkspacePane.test-support";
import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerRulesWorkspacePane rule tools", () => {
  beforeEach(resetPlannerState);

  it("edits existing relationship rules from the inspector", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-edit-rule-0"]').trigger("click");

    expect(stateMocks.plannerState.beginRelationshipRuleEdit).toHaveBeenCalledWith("rule-1");
  });

  it("edits the persisted near-teacher rule from the summary panel", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-edit-near-teacher-0"]').trigger("click");

    expect(stateMocks.plannerState.beginNearTeacherEdit).toHaveBeenCalledWith();
  });

  it("activates the near-teacher tool without entering persisted edit mode", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="phone-rules-tool-near_teacher"]').trigger("click");

    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("near_teacher");
    expect(stateMocks.plannerState.beginNearTeacherEdit).not.toHaveBeenCalled();
  });

  it("removes the consolidated near-teacher rule directly from the inspector", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-delete-near-teacher-0"]').trigger("click");

    expect(stateMocks.plannerState.clearNearTeacherRule).toHaveBeenCalledWith();
  });

  it("keeps the tool rail on a bounded sticky lane beside the map and reserves the summary panel height before rules exist", () => {
    stateMocks.plannerState.seatingPreferences = [];
    stateMocks.plannerState.relationshipRules = [];
    stateMocks.plannerState.pendingRelationshipStudentIds = [];
    stateMocks.plannerState.activeSeatingSmartTool = null;

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.get('[data-test="rules-workspace-layout"]').classes()).toContain("planner-rules-layout-row");
    wrapper.get(".planner-rules-tool-column");
    expect(wrapper.get('[data-test="rules-tool-rail"]').classes()).toEqual(
      expect.arrayContaining(["planner-rules-tool-lane", "flex", "flex-col"]),
    );
    expect(wrapper.get('[data-test="rules-summary-empty-state"]').classes()).toContain("min-h-full");
  });

  it("starts the rules workspace with a blank near-teacher tool instead of editing persisted rules", () => {
    stateMocks.plannerState.activeSeatingSmartTool = null;
    stateMocks.plannerState.pendingRelationshipStudentIds = [];

    mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("near_teacher");
    expect(stateMocks.plannerState.beginNearTeacherEdit).not.toHaveBeenCalled();
  });
});
