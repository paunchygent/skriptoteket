import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { UiDenseActionButton } from "../../../components/ui";
import PlannerPhoneOverviewSetupPanel from "./PlannerPhoneOverviewSetupPanel.vue";

function mountPanel() {
  return mount(PlannerPhoneOverviewSetupPanel, {
    props: {
      selectedRoster: null,
      selectedRosterId: null,
      availableRosters: [],
      selectedTemplate: null,
      selectedTemplateId: null,
      availableTemplates: [],
      isLoadingWorkspace: false,
    },
  });
}

describe("PlannerPhoneOverviewSetupPanel", () => {
  it("uses shared touch controls for all roster and classroom actions", () => {
    const wrapper = mountPanel();
    const actions = wrapper.findAllComponents(UiDenseActionButton);

    expect(actions).toHaveLength(6);
    for (const action of actions) {
      expect(action.props("size")).toBe("touch");
      expect(action.text()).toBeTruthy();
    }
  });

  it("retains creation events and disables edit/delete without a selection", async () => {
    const wrapper = mountPanel();

    for (const target of ["roster", "template"]) {
      expect(wrapper.get(`[data-test="phone-overview-edit-${target}"]`).attributes("disabled")).toBeDefined();
      expect(wrapper.get(`[data-test="phone-overview-delete-${target}"]`).attributes("disabled")).toBeDefined();
      await wrapper.get(`[data-test="phone-overview-create-${target}"]`).trigger("click");
      expect(wrapper.emitted(`create-${target}`)).toEqual([[]]);
    }
  });
});
