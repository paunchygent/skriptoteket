import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ChatComposer from "./ChatComposer.vue";

function mountComposer() {
  return mount(ChatComposer, {
    props: { isStreaming: false, isEditOpsLoading: false, canClear: true },
  });
}

describe("ChatComposer shared controls", () => {
  it.each([0, 1])("names the code-assistant message field in Swedish in mode %i", async (modeIndex) => {
    const wrapper = mountComposer();
    try {
      const modes = wrapper.get('[role="radiogroup"]').findAll('[role="radio"]');
      await modes[modeIndex]!.trigger("click");
      const textarea = wrapper.get("textarea").element;
      const labelledBy = textarea.getAttribute("aria-labelledby");
      const name = textarea.getAttribute("aria-label")
        ?? (labelledBy
          ? labelledBy.split(/\s+/).map((id) => wrapper.find(`[id="${id}"]`).text()).join(" ")
          : Array.from(textarea.labels ?? []).map((label) => label.textContent).join(" "));
      expect(name.trim()).toMatch(/meddelande|fråga|instruktion|kodassistent/i);
    } finally {
      wrapper.unmount();
    }
  });

  it("routes keyboard-selected edit requests without losing the draft, then sends chat", async () => {
    const wrapper = mountComposer();
    await wrapper.get("textarea").setValue("  Fixa en bugg  ");
    const modes = wrapper.get('[role="radiogroup"]').findAll('[role="radio"]');

    await modes[0]!.trigger("keydown", { key: "ArrowRight" });
    expect(modes[1]!.attributes("aria-checked")).toBe("true");
    await wrapper.get('button[aria-label="Föreslå ändringar"]').trigger("click");

    expect(wrapper.emitted("requestEditOps")).toEqual([["Fixa en bugg"]]);
    expect(wrapper.emitted("send")).toBeUndefined();
    expect(wrapper.get("textarea").element.value).toBe("  Fixa en bugg  ");

    await modes[1]!.trigger("keydown", { key: "Home" });
    await wrapper.get('button[aria-label="Skicka"]').trigger("click");
    expect(wrapper.emitted("send")).toEqual([["Fixa en bugg"]]);
    expect(wrapper.get("textarea").element.value).toBe("");
    wrapper.unmount();
  });

  it.each(["isStreaming", "isEditOpsLoading"] as const)(
    "blocks mode, clear and submission while %s, then restores actions",
    async (busyProp) => {
      const wrapper = mountComposer();
      await wrapper.get("textarea").setValue("Behåll mig");
      await wrapper.setProps({ [busyProp]: true });

      const modes = wrapper.get('[role="radiogroup"]').findAll('[role="radio"]');
      for (const mode of modes) expect(mode.attributes("disabled")).toBeDefined();
      await modes[0]!.trigger("keydown", { key: "ArrowRight" });
      expect(modes[0]!.attributes("aria-checked")).toBe("true");
      const submit = wrapper.get('button[aria-label="Skicka"]');
      expect(submit.attributes("disabled")).toBeDefined();
      await submit.trigger("click");
      await wrapper.get("textarea").trigger("keydown", { key: "Enter" });
      const clear = wrapper.findAll("button").find((button) => button.text() === "Ny chatt")!;
      expect(clear.attributes("disabled")).toBeDefined();
      await clear.trigger("click");
      expect(wrapper.emitted("send")).toBeUndefined();
      expect(wrapper.emitted("requestEditOps")).toBeUndefined();
      expect(wrapper.emitted("clear")).toBeUndefined();

      await wrapper.setProps({ [busyProp]: false });
      await wrapper.get('button[aria-label="Skicka"]').trigger("click");
      expect(wrapper.emitted("send")).toEqual([["Behåll mig"]]);
      wrapper.unmount();
    },
  );

  it("keeps cancellation and clearing distinct from submission", async () => {
    const wrapper = mountComposer();
    await wrapper.setProps({ isStreaming: true });
    await wrapper.findAll("button").find((button) => button.text() === "Avbryt")!.trigger("click");
    expect(wrapper.emitted("cancel")).toEqual([[]]);
    expect(wrapper.emitted("clear")).toBeUndefined();

    await wrapper.setProps({ isStreaming: false });
    await wrapper.findAll("button").find((button) => button.text() === "Ny chatt")!.trigger("click");
    expect(wrapper.emitted("clear")).toEqual([[]]);
    expect(wrapper.emitted("send")).toBeUndefined();
    wrapper.unmount();
  });
});
