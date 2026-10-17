/** Phone rules student-pool selection, drop targets, and idempotent removal. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { resetPlannerState, stateMocks } from "./PlannerRulesWorkspacePane.test-support";
import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerRulesWorkspacePane phone selection", () => {
  beforeEach(resetPlannerState);

  it("renders the phone rules workspace with a default-open student list and sticky drop target", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.get('[data-test="phone-rules-workspace"]').text()).toContain(
      "Reglerna gäller hela klassen.",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-keep_apart"]').classes()).toContain(
      "planner-phone-rule-row-active",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-keep_apart"]').html()).toContain(
      "text-button-primary-text/75",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-near_teacher"]').html()).toContain(
      "lucide-user-star",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-near_teacher"]').html()).not.toContain(
      "lucide-school",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-keep_near"]').html()).toContain(
      "lucide-magnet",
    );
    expect(wrapper.get('[data-test="phone-rules-tool-keep_near"]').html()).not.toContain(
      "lucide-link-2",
    );
    expect(wrapper.get('[data-test="phone-rules-selection"]').classes()).toContain(
      "planner-phone-rules-selection",
    );
    expect(wrapper.get('[data-test="phone-rules-selected-student"]').text()).toContain(
      "Alan Turing",
    );
    expect(wrapper.get('[data-test="phone-rules-student-list"]').text()).toContain("Ada Lovelace");

    await wrapper.get('[data-test="phone-rules-tool-keep_near"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-student-pool"]').trigger("drop", {
      dataTransfer: { getData: () => "student-1", dropEffect: "move" },
    });
    await wrapper.get('[data-test="phone-rules-selection"]').trigger("drop", {
      dataTransfer: { getData: () => "student-1", dropEffect: "move" },
    });
    await wrapper.get('[data-test="phone-rules-clear-selection"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-commit-rule"]').trigger("click");

    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("keep_near");
    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).toHaveBeenCalledWith("student-1");
    expect(stateMocks.plannerState.clearPendingRuleCandidates).toHaveBeenCalledWith();
    expect(stateMocks.plannerState.commitPendingRelationshipRule).toHaveBeenCalledWith();
  });

  it("removes phone selected candidates with an idempotent remove action", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="phone-rules-selected-student"] button').trigger("click");

    expect(stateMocks.plannerState.removePendingRuleCandidate).toHaveBeenCalledWith("student-2");
    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).not.toHaveBeenCalled();
  });

  it("removes already-selected phone student cards instead of toggling them back in", async () => {
    stateMocks.plannerState.isStudentInPendingRuleCandidates.mockImplementation(
      (studentId: string) => studentId === "student-2",
    );

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper
      .findAll('[data-test="phone-rules-student-pool"] button')[1]
      .trigger("click");

    expect(stateMocks.plannerState.removePendingRuleCandidate).toHaveBeenCalledWith("student-2");
    expect(stateMocks.plannerState.handleSeatingSmartToolStudentSelection).not.toHaveBeenCalled();
  });
});
