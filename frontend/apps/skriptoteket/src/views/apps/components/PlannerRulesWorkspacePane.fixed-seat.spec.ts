/** Fixed-seat rule prompting, summary actions, pending binding, and phone map flow. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { resetPlannerState, stateMocks } from "./PlannerRulesWorkspacePane.test-support";
import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerRulesWorkspacePane fixed-seat flow", () => {
  beforeEach(resetPlannerState);

  it("routes Fast plats from Planeringskarta through the classroom-view prompt", async () => {
    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            props: ["mapView"],
            emits: ["update:mapView"],
            template: `
              <div>
                <button
                  type="button"
                  data-test="rules-map-view-planning"
                  @click="$emit('update:mapView', 'planning_map')"
                >
                  Planeringskarta
                </button>
                <div data-test='rules-map-canvas-stub'>{{ mapView }}</div>
              </div>
            `,
          },
        },
      },
    });

    await wrapper.get('[data-test="rules-map-view-planning"]').trigger("click");
    await wrapper.get('[data-test="rules-tool-fixed_seat"]').trigger("click");

    expect(wrapper.get('[data-test="rules-fixed-seat-switch-prompt"]').text()).toContain("Fast plats kräver en fysisk plats. Vill du byta till klassrumsvyn?");
    expect(wrapper.get('[data-test="rules-fixed-seat-switch-prompt"]').classes()).toContain("bg-canvas");
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).not.toHaveBeenCalledWith("fixed_seat");

    await wrapper.get('[data-test="rules-fixed-seat-switch-no"]').trigger("click");

    expect(wrapper.find('[data-test="rules-fixed-seat-switch-prompt"]').exists()).toBe(false);
    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("planning_map");

    await wrapper.get('[data-test="rules-tool-fixed_seat"]').trigger("click");
    await wrapper.get('[data-test="rules-fixed-seat-switch-yes"]').trigger("click");

    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("seating_arrangement");
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).toHaveBeenCalledWith("fixed_seat");
  });

  it("renders fixed-seat rules in the active rules summary", async () => {
    stateMocks.plannerState.fixedSeatRules = [
      {
        id: "fixed-1",
        template_id: "template-1",
        student_id: "student-2",
        seat_id: "seat-2",
      },
    ];

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.get('[data-test="rules-fixed-seat-card"]').text()).toContain("Fast plats");
    expect(wrapper.get('[data-test="rules-fixed-seat-card"]').text()).toContain("Alan Turing");

    await wrapper.get('[data-test="rules-edit-fixed-seat-fixed-1"]').trigger("click");
    await wrapper.get('[data-test="rules-delete-fixed-seat-fixed-1"]').trigger("click");

    expect(stateMocks.plannerState.beginFixedSeatRuleEdit).toHaveBeenCalledWith("fixed-1");
    expect(stateMocks.plannerState.deleteFixedSeatRule).toHaveBeenCalledWith("fixed-1");
  });

  it("shows fixed-seat pending binding, clear selection, and explicit create action", async () => {
    stateMocks.plannerState.activeSeatingSmartTool = "fixed_seat";
    stateMocks.plannerState.pendingRelationshipStudentIds = [];
    stateMocks.plannerState.pendingFixedSeatStudentId = "student-1";
    stateMocks.plannerState.pendingFixedSeatSeatId = "seat-2";
    stateMocks.plannerState.canCommitPendingFixedSeatRule = true;

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });
    expect(wrapper.get('[data-test="rules-fixed-seat-panel"]').text()).toContain("Ada Lovelace");
    expect(wrapper.get('[data-test="rules-fixed-seat-panel"]').text()).toContain("plats-2");
    expect(wrapper.get('[data-test="rules-tool-rail"]').text()).toContain("Pågående fast plats");
    expect(wrapper.get('[data-test="rules-tool-rail"]').text()).not.toContain("2 valda");
    expect(wrapper.get('[data-test="rules-fixed-seat-help"]').text()).toBe("Skapa regel låser eleven till platsen.");
    expect(wrapper.get('[data-test="rules-fixed-seat-pending-binding"]').text()).not.toContain("->");
    expect(wrapper.get('[data-test="rules-fixed-seat-pending-link"]').html()).toContain("lucide-link-2");
    expect(wrapper.get('[data-test="rules-commit-fixed-seat"]').text()).toBe("Skapa regel");
    expect(wrapper.get('[data-test="rules-commit-fixed-seat"]').attributes("disabled")).toBeUndefined();
    expect(wrapper.get('[data-test="rules-clear-selection"]').attributes("disabled")).toBeUndefined();
    await wrapper.get('[data-test="rules-clear-selection"]').trigger("click");
    await wrapper.get('[data-test="rules-commit-fixed-seat"]').trigger("click");
    expect(stateMocks.plannerState.commitPendingFixedSeatRule).toHaveBeenCalledWith();
  });

  it("renders the approved phone fixed-seat map flow without replacing relationship tools", async () => {
    stateMocks.plannerState.activeSeatingSmartTool = "fixed_seat";
    stateMocks.plannerState.pendingRelationshipStudentIds = [];
    stateMocks.plannerState.pendingFixedSeatStudentId = "student-1";
    stateMocks.plannerState.pendingFixedSeatSeatId = "seat-2";
    stateMocks.plannerState.canCommitPendingFixedSeatRule = true;

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    expect(wrapper.find('[data-test="phone-rules-selection"]').exists()).toBe(false);
    expect(wrapper.get('[data-test="phone-fixed-seat-panel"]').text()).toContain("Välj elev och plats.");
    expect(wrapper.get('[data-test="phone-fixed-seat-pending-student"]').text()).toContain("Ada Lovelace");
    expect(wrapper.get('[data-test="phone-fixed-seat-pending-seat"]').text()).toContain("plats-2");
    expect(wrapper.findAll('button[data-test^="phone-fixed-seat-map-seat-seat-"]')).toHaveLength(2);
    expect(wrapper.get('[data-test="phone-rules-commit-fixed-seat"]').attributes("disabled")).toBeUndefined();

    await wrapper.get('[data-test="phone-fixed-seat-map-seat-seat-1"]').trigger("click");
    await wrapper.get('[data-test="phone-rules-commit-fixed-seat"]').trigger("click");

    expect(stateMocks.plannerState.selectFixedSeatRuleSeat).toHaveBeenCalledWith("seat-1");
    expect(stateMocks.plannerState.commitPendingFixedSeatRule).toHaveBeenCalledWith();
  });

  it("explains that Fast plats requires a classroom on phone", async () => {
    stateMocks.plannerState.template = null;

    const wrapper = mount(PlannerRulesWorkspacePane, {
      global: {
        stubs: {
          PlannerRulesMapCanvas: {
            template: "<div data-test='rules-map-canvas-stub' />",
          },
        },
      },
    });

    await wrapper.get('[data-test="phone-rules-tool-fixed_seat"]').trigger("click");

    expect(wrapper.get('[data-test="phone-rules-fixed-seat-classroom-required"]').text()).toContain(
      "Fast plats kräver ett klassrum.",
    );
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).not.toHaveBeenCalledWith("fixed_seat");
  });
});
