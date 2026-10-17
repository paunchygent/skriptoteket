import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";

import ReagentPrepChefSdsModal from "./ReagentPrepChefSdsModal.vue";

const wrappers: ReturnType<typeof mount>[] = [];

afterEach(() => {
  wrappers.forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  document.body.replaceChildren();
});

describe("ReagentPrepChefSdsModal", () => {
  it("forwards the shared close action without treating content clicks as dismissal", async () => {
    const wrapper = mount(ReagentPrepChefSdsModal, {
      props: { isOpen: true, title: "SDS: NaCl", markdown: "Säkerhetsdata" },
      global: { stubs: { teleport: true } },
    });
    wrappers.push(wrapper);

    await wrapper.get("h2").trigger("click");
    expect(wrapper.emitted("close")).toBeUndefined();

    await wrapper.get('button[aria-label="Stäng SDS"]').trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);

    await wrapper.get('[role="dialog"]').trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);

    wrapper.get('[role="dialog"]').element.parentElement!.click();
    await nextTick();
    expect(wrapper.emitted("close")).toHaveLength(2);
  });

  it("names the dialog from its visible title and returns focus after Escape dismissal", async () => {
    const opener = document.createElement("button");
    opener.textContent = "Öppna SDS";
    document.body.appendChild(opener);
    opener.focus();

    const wrapper = mount(ReagentPrepChefSdsModal, {
      props: { isOpen: false, title: "SDS: NaCl", markdown: "Säkerhetsdata" },
      attachTo: document.body,
      global: { stubs: { teleport: true } },
    });
    wrappers.push(wrapper);
    await wrapper.setProps({ isOpen: true });

    const dialog = wrapper.get('[role="dialog"]');
    const heading = wrapper.get("h2");
    const labelId = dialog.attributes("aria-labelledby");
    expect.soft(dialog.attributes("aria-modal")).toBe("true");
    expect.soft(labelId).toBeTruthy();
    expect.soft(heading.attributes("id")).toBe(labelId);
    expect.soft(document.getElementById(labelId ?? "")).toBe(heading.element);

    wrapper.get<HTMLButtonElement>('button[aria-label="Stäng SDS"]').element.focus();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await nextTick();
    expect.soft(wrapper.emitted("close")).toHaveLength(1);

    await wrapper.setProps({ isOpen: false });
    expect.soft(document.activeElement).toBe(opener);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await nextTick();
    expect.soft(wrapper.emitted("close")).toHaveLength(1);
  });
});
