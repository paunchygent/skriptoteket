import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import { UiSegmentedToggle, type UiSegmentedToggleOption } from "./shared";

const options: UiSegmentedToggleOption[] = [
  { value: "overview", label: "Översikt" },
  {
    value: "grouping",
    label: "Grupper",
    disabled: true,
    title: "Skapa först en klasslista.",
  },
  { value: "seating", label: "Sittplatser" },
  { value: "rules", label: "Regler" },
];

const cleanups: (() => void)[] = [];
afterEach(() => {
  for (const cleanup of cleanups.splice(0)) cleanup();
});

function mountToggle(initialValue: string) {
  const toggleOptions = ref(options);
  const groupDisabled = ref(false);
  const host = mount(defineComponent({
    setup() {
      const selected = ref(initialValue);
      return () => h(UiSegmentedToggle, {
        modelValue: selected.value,
        options: toggleOptions.value,
        disabled: groupDisabled.value,
        ariaLabel: "Välj läge",
        "onUpdate:modelValue": (value: string) => { selected.value = value; },
      });
    },
  }), { attachTo: document.body });
  cleanups.push(() => host.unmount());
  const toggle = host.getComponent(UiSegmentedToggle);
  const radio = (value: string) => {
    const label = options.find((option) => option.value === value)?.label;
    const button = toggle.findAll<HTMLButtonElement>('[role="radio"]')
      .find((candidate) => candidate.text() === label);
    if (!button) throw new Error(`No radio with label for option "${value}"`);
    return button;
  };
  const tabStops = () => toggle.findAll<HTMLButtonElement>('[role="radio"]')
    .filter((button) => button.element.tabIndex >= 0)
    .map((button) => button.text());
  return { toggle, radio, tabStops, toggleOptions, groupDisabled };
}

describe("shared UiSegmentedToggle keyboard contract", () => {
  it("exposes only the selected enabled option to Tab, including after selection changes", async () => {
    const { radio, tabStops } = mountToggle("seating");

    // jsdom does not perform native Tab traversal: inspect its DOM tab order.
    expect(tabStops()).toEqual(["Sittplatser"]);
    expect(radio("grouping").element.tabIndex).toBe(-1);
    await radio("seating").trigger("keydown", { key: "ArrowRight" });
    expect(tabStops()).toEqual(["Regler"]);
    expect(radio("seating").element.tabIndex).toBe(-1);
  });

  it("keeps the first enabled radio tabbable when the selected option is disabled, without changing the model", async () => {
    const { toggle, radio, tabStops } = mountToggle("grouping");

    expect(tabStops()).toEqual(["Översikt"]);
    expect(radio("overview").element.disabled).toBe(false);
    expect(radio("grouping").attributes("aria-checked")).toBe("true");
    expect(toggle.emitted("update:modelValue")).toBeUndefined();

    radio("overview").element.focus();
    await radio("overview").trigger("keydown", { key: "ArrowRight" });
    expect(toggle.emitted("update:modelValue")).toEqual([["seating"]]);
    expect(radio("seating").attributes("aria-checked")).toBe("true");
    expect(document.activeElement).toBe(radio("seating").element);
    expect(tabStops()).toEqual(["Sittplatser"]);
  });

  it("restores one enabled tab stop when the selected option becomes disabled by a props change", async () => {
    const { toggle, radio, tabStops, toggleOptions } = mountToggle("seating");
    expect(tabStops()).toEqual(["Sittplatser"]);

    toggleOptions.value = options.map((option) => option.value === "seating"
      ? { ...option, disabled: true }
      : option);
    await nextTick();

    expect(radio("seating").element.disabled).toBe(true);
    expect(radio("seating").attributes("aria-checked")).toBe("true");
    expect(tabStops()).toEqual(["Översikt"]);
    expect(radio("overview").element.disabled).toBe(false);
    expect(toggle.emitted("update:modelValue")).toBeUndefined();
  });

  it("removes every radio from the tab order when the whole group is disabled", async () => {
    const { toggle, tabStops, groupDisabled } = mountToggle("seating");
    expect(tabStops()).toEqual(["Sittplatser"]);

    groupDisabled.value = true;
    await nextTick();

    expect(tabStops()).toEqual([]);
    expect(toggle.findAll<HTMLButtonElement>('[role="radio"]')
      .every((button) => button.element.disabled)).toBe(true);
    expect(toggle.emitted("update:modelValue")).toBeUndefined();
  });

  it.each([
    ["ArrowRight", ["seating", "rules", "overview"]],
    ["ArrowDown", ["seating", "rules", "overview"]],
    ["ArrowLeft", ["rules", "seating", "overview"]],
    ["ArrowUp", ["rules", "seating", "overview"]],
  ] as const)("%s skips the disabled middle option, wraps, and moves focus with selection", async (key, destinations) => {
    const { toggle, radio } = mountToggle("overview");
    let current = "overview";
    radio(current).element.focus();

    for (const destination of destinations) {
      await radio(current).trigger("keydown", { key });
      expect(toggle.emitted("update:modelValue")?.at(-1)).toEqual([destination]);
      expect(toggle.findAll('[role="radio"][aria-checked="true"]').map((button) => button.text()))
        .toEqual([radio(destination).text()]);
      expect(document.activeElement).toBe(radio(destination).element);
      expect(radio(destination).element.tabIndex).toBe(0);
      expect(radio("grouping").attributes("aria-checked")).toBe("false");
      current = destination;
    }
    expect(toggle.emitted("update:modelValue")).toEqual(destinations.map((value) => [value]));
  });

  it.each([
    ["Home", "overview"],
    ["End", "rules"],
  ] as const)("%s selects the enabled endpoint and moves focus there", async (key, destination) => {
    const { toggle, radio } = mountToggle("seating");
    radio("seating").element.focus();
    await radio("seating").trigger("keydown", { key });

    expect(toggle.emitted("update:modelValue")).toEqual([[destination]]);
    expect(radio(destination).attributes("aria-checked")).toBe("true");
    expect(radio("seating").attributes("aria-checked")).toBe("false");
    expect(radio("grouping").attributes("aria-checked")).toBe("false");
    expect(document.activeElement).toBe(radio(destination).element);
    expect(radio(destination).element.tabIndex).toBe(0);
    expect(radio("seating").element.tabIndex).toBe(-1);
  });

  it("links the disabled option to guidance present in the DOM, not only a title", () => {
    const { radio } = mountToggle("overview");
    const disabledOption = radio("grouping");
    expect(disabledOption.element.disabled).toBe(true);
    const describedBy = disabledOption.attributes("aria-describedby");
    expect(describedBy).toBeTruthy();
    const descriptions = describedBy!.split(/\s+/).map((id) => document.getElementById(id));
    expect(descriptions.every((description) => description !== null)).toBe(true);
    expect(descriptions.map((description) => description!.textContent?.trim()))
      .toContain(options[1]!.title);
  });
});
