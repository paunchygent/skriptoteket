import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HelpTopicLoadError from "./HelpTopicLoadError.vue";
import { useHelp } from "../useHelp";

describe("HelpTopicLoadError", () => {
  it("announces the failed topic and lets the teacher recover to the index without closing help", async () => {
    const help = useHelp();
    help.isOpen.value = true;
    help.showTopic("login");
    const wrapper = mount(HelpTopicLoadError);
    try {
      const failure = wrapper.get('[role="alert"]');
      expect(failure.text()).not.toBe("");
      expect(failure.attributes("aria-live")).toBe("assertive");
      expect(failure.attributes("aria-atomic")).toBe("true");
      await wrapper.get('a[href="#help-index"]').trigger("click");
      expect(help.activeTopic.value).toBeNull();
      expect(help.isOpen.value).toBe(true);
    } finally {
      wrapper.unmount();
      help.close({ restoreFocus: false });
    }
  });
});
