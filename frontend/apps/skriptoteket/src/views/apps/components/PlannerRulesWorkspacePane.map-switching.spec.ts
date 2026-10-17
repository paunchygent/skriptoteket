/** Rules workspace classroom/planning map selection and explicit switching. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { resetPlannerState, stateMocks } from "./PlannerRulesWorkspacePane.test-support";
import PlannerRulesWorkspacePane from "./PlannerRulesWorkspacePane.vue";

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

describe("PlannerRulesWorkspacePane map switching", () => {
  beforeEach(resetPlannerState);

  it("defaults to Klassrumsvy when a classroom exists and preserves explicit switches", async () => {
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
                <button
                  type="button"
                  data-test="rules-map-view-seating"
                >
                  Klassrumsvy
                </button>
                <div data-test='rules-map-canvas-stub'>{{ mapView }}</div>
              </div>
            `,
          },
        },
      },
    });

    expect(wrapper.find('[data-test="rules-summary-panel"]').exists()).toBe(true);
    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("seating_arrangement");
    expect(wrapper.text()).toContain("2 valda");
    expect(wrapper.text()).toContain("Nära läraren");
    expect(wrapper.text()).not.toContain("Närmare läraren");
    expect(wrapper.text()).not.toContain("totalt");
    expect(
      wrapper.find('[data-test="rules-tool-rail"] [data-test="rules-pending-panel"]').exists(),
    ).toBe(true);
    expect(
      wrapper.find('[data-test="rules-summary-panel"] [data-test="rules-commit-rule"]').exists(),
    ).toBe(false);

    await wrapper.get('[data-test="rules-map-view-planning"]').trigger("click");

    expect(wrapper.get("[data-test='rules-map-canvas-stub']").text()).toBe("planning_map");
    expect(stateMocks.plannerState.setActiveSeatingSmartTool).not.toHaveBeenCalled();
    expect(stateMocks.plannerState.clearPendingRelationshipSelection).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("2 valda");
  });
});
