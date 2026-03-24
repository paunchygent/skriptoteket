import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerTemplateOverviewPanel from "./PlannerTemplateOverviewPanel.vue";

describe("PlannerTemplateOverviewPanel", () => {
  it("renders the compact overview preview through the shared room surface seam", () => {
    const wrapper = mount(PlannerTemplateOverviewPanel, {
      props: {
        selectedTemplate: {
          id: "template-1",
          name: "Sal A",
          grid_cols: 14,
          grid_rows: 9,
          seats: [
            { id: "seat-1", x: 192, y: 288 },
          ],
          fixtures: [
            { id: "door-1", type: "door", x: 0, y: 192, width: 96, height: 96, label: null },
          ],
        },
        selectedTemplateId: "template-1",
        availableTemplates: [],
        description: "Kompakt förhandsvisning",
        isLoadingWorkspace: false,
      },
    });

    expect(wrapper.get("[data-test='overview-classroom-preview']").html()).toContain("Dörr");
    expect(wrapper.html()).toContain("writing-mode: vertical-rl;");
  });
});
