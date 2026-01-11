import { describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { mountWithContext } from "../../test/utils";
import ChatDrawer from "./ChatDrawer.vue";

describe("ChatDrawer", () => {
  it("keeps draft on edit-ops request and clears only when clearDraftToken changes", async () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: false,
        disabledMessage: null,
        error: null,
        clearDraftToken: 0,
      },
    });

    const textarea = wrapper.find("textarea");
    await textarea.setValue("Fixa en bugg");
    await nextTick();

    const requestButton = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Föreslå"));

    expect(requestButton, "Missing 'Föreslå ändringar' button").toBeTruthy();

    await requestButton!.trigger("click");
    expect(textarea.element.value).toBe("Fixa en bugg");
    expect(wrapper.emitted("requestEditOps")?.[0]).toEqual(["Fixa en bugg"]);

    await wrapper.setProps({ clearDraftToken: 1 });
    await nextTick();
    expect(wrapper.find("textarea").element.value).toBe("");
  });

  it("shows a slow-request hint for edit-ops", () => {
    const wrapper = mountWithContext(ChatDrawer, {
      props: {
        variant: "column",
        isOpen: true,
        isCollapsed: false,
        messages: [],
        isStreaming: false,
        isEditOpsLoading: true,
        editOpsIsSlow: true,
        disabledMessage: null,
        error: null,
        clearDraftToken: 0,
      },
    });

    expect(wrapper.text()).toContain("Skapar förslag...");
    expect(wrapper.text()).toContain("Tar lite längre tid");
  });
});
