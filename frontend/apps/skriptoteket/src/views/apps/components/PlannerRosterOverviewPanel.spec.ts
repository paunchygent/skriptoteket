import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerRosterOverviewPanel from "./PlannerRosterOverviewPanel.vue";

describe("PlannerRosterOverviewPanel", () => {
  it("keeps class import inside the create/edit workflow instead of a separate overview button", () => {
    const wrapper = mount(PlannerRosterOverviewPanel, {
      props: {
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
      },
    });

    expect(wrapper.text()).toContain("Ny klasslista");
    expect(wrapper.text()).toContain("Redigera klass");
    expect(wrapper.text()).not.toContain("Importera från fil");
  });
});
