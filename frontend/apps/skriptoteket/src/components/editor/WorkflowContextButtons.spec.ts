import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WorkflowContextButtons from "./WorkflowContextButtons.vue";

function mountActions(enabled: boolean) {
  return mount(WorkflowContextButtons, {
    props: {
      canSubmitReview: enabled,
      submitReviewTooltip: null,
      canPublish: enabled,
      canRequestChanges: enabled,
      canRollback: false,
      isSubmitting: false,
    },
  });
}

describe("WorkflowContextButtons shared actions", () => {
  it("exposes unavailable actions as disabled controls that cannot dispatch", async () => {
    const wrapper = mountActions(false);
    const buttons = wrapper.findAll("button");
    expect(buttons.map((button) => button.text())).toEqual(["Begär publicering", "Publicera", "Avslå"]);
    for (const button of buttons) {
      expect(button.attributes("disabled")).toBeDefined();
      await button.trigger("click");
    }
    expect(wrapper.emitted("action")).toBeUndefined();
    wrapper.unmount();
  });

  it("preserves each command and blocks repeat actions during submission", async () => {
    const wrapper = mountActions(true);
    for (const button of wrapper.findAll("button")) await button.trigger("click");
    expect(wrapper.emitted("action")).toEqual([["submit_review"], ["publish"], ["request_changes"]]);

    await wrapper.setProps({ isSubmitting: true });
    for (const button of wrapper.findAll("button")) {
      expect(button.attributes("disabled")).toBeDefined();
      await button.trigger("click");
    }
    expect(wrapper.emitted("action")).toHaveLength(3);
    wrapper.unmount();
  });
});
