/**
 * Micro-help disclosure behavior tests.
 *
 * These checks keep the reusable field-level help pattern keyboard-friendly and
 * suitable for migrating one-off form help without duplicating listeners.
 */
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";

import MicroHelp from "./MicroHelp.vue";

async function flushUi(): Promise<void> {
  await nextTick();
  await Promise.resolve();
  await nextTick();
}

describe("MicroHelp", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("opens approved field help from the trigger", async () => {
    const wrapper = mount(MicroHelp, {
      attachTo: document.body,
      props: {
        id: "suggestion-description-help",
        label: "Visa hjälp för beskrivning",
        title: "Beskrivning",
      },
      slots: {
        default: "Vad ska verktyget göra, för vem, och när i arbetet används det?",
      },
    });

    const trigger = wrapper.get('button[aria-label="Visa hjälp för beskrivning"]');
    expect(trigger.attributes("aria-expanded")).toBe("false");

    await trigger.trigger("click");
    await flushUi();

    expect(trigger.attributes("aria-expanded")).toBe("true");
    expect(wrapper.text()).toContain("Beskrivning");
    expect(wrapper.text()).toContain("Vad ska verktyget göra");
    expect(wrapper.get('[role="dialog"]').attributes("aria-labelledby")).toBe(
      "suggestion-description-help-title",
    );

    wrapper.unmount();
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const wrapper = mount(MicroHelp, {
      attachTo: document.body,
      props: {
        id: "field-help",
        label: "Visa hjälp",
      },
      slots: {
        default: "Kort hjälptext.",
      },
    });

    const trigger = wrapper.get('button[aria-label="Visa hjälp"]');
    await trigger.trigger("click");
    await flushUi();

    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    await flushUi();

    expect(trigger.attributes("aria-expanded")).toBe("false");
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(document.activeElement).toBe(trigger.element);

    wrapper.unmount();
  });

  it("closes when the user clicks outside the help disclosure", async () => {
    const wrapper = mount(MicroHelp, {
      attachTo: document.body,
      props: {
        id: "outside-help",
        label: "Visa hjälp",
      },
      slots: {
        default: "Kort hjälptext.",
      },
    });

    await wrapper.get('button[aria-label="Visa hjälp"]').trigger("click");
    await flushUi();
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true);

    document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flushUi();

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);

    wrapper.unmount();
  });
});
