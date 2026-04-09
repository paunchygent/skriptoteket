import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerRosterOverviewPanel from "./PlannerRosterOverviewPanel.vue";

function buildProps(overrides: Record<string, unknown> = {}) {
  return {
    title: "SA24D",
    countLabel: "1 elev",
    description: "Beskrivning",
    selectedRoster: {
      id: "roster-1",
      name: "SA24D",
      students: [{ id: "student-1", display_name: "Ada" }],
    },
    selectedRosterId: "roster-1",
    availableRosters: [
      {
        id: "roster-1",
        name: "SA24D",
        students: [{ id: "student-1", display_name: "Ada" }],
      },
    ],
    selectedRosterPreviewNames: ["Ada"],
    isLoadingWorkspace: false,
    ...overrides,
  };
}

describe("PlannerRosterOverviewPanel", () => {
  it("keeps class import inside the create/edit workflow instead of a separate overview button", () => {
    const wrapper = mount(PlannerRosterOverviewPanel, {
      props: buildProps({ showActions: true }),
    });

    expect(wrapper.text()).toContain("Ny klasslista");
    expect(wrapper.text()).toContain("Redigera");
    expect(wrapper.text()).not.toContain("Importera från fil");
  });

  it("can hide the action footer when overview capabilities disable roster actions", () => {
    const wrapper = mount(PlannerRosterOverviewPanel, {
      props: buildProps({ showActions: false }),
    });

    expect(wrapper.text()).not.toContain("Ny klasslista");
    expect(wrapper.find('[data-test="overview-edit-roster"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="overview-delete-roster"]').exists()).toBe(false);
  });

  it("omits the uppercase metadata label when no count label is provided", () => {
    const wrapper = mount(PlannerRosterOverviewPanel, {
      props: buildProps({
        title: "Ingen klass vald",
        countLabel: null,
        description: null,
        selectedRoster: null,
        selectedRosterId: null,
        availableRosters: [],
        selectedRosterPreviewNames: [],
      }),
    });

    expect(wrapper.text()).toContain("Ingen klass vald");
    expect(wrapper.text()).not.toContain("VÄLJ EN KLASSLISTA");
  });
});
