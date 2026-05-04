/**
 * Planner top-panel tests.
 *
 * These tests lock the workspace header's close affordance so it uses the
 * shared icon-button primitive while retaining the existing exit behavior.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import PlannerTopPanel from "./PlannerTopPanel.vue";

function mountTopPanel(props?: Partial<InstanceType<typeof PlannerTopPanel>["$props"]>) {
  return mount(PlannerTopPanel, {
    props: {
      title: "SA25D",
      contextLabel: "Sal 101",
      modeValue: "rules",
      ...props,
    },
  });
}

describe("PlannerTopPanel", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("keeps the exit action as an accessible icon button", async () => {
    const wrapper = mountTopPanel();
    const exitButton = wrapper.get('[data-test="planner-exit"]');

    expect(exitButton.text()).toBe("");
    expect(exitButton.attributes("aria-label")).toBe("Avsluta");
    expect(exitButton.attributes("title")).toBe("Avsluta");
    expect(exitButton.classes()).toContain("planner-btn-icon-md");

    await exitButton.trigger("click");

    expect(wrapper.emitted("exit")).toHaveLength(1);
  });

  it("opens the phone mode sheet and uses the same disabled workspace contract", async () => {
    const wrapper = mountTopPanel({
      modeValue: "grouping",
      seatingDisabledReason: "Skapa eller välj först ett klassrum.",
    });

    expect(wrapper.get('[data-test="planner-phone-active-mode"]').text()).toBe("Grupper");

    await wrapper.get('[data-test="planner-phone-mode-sheet-trigger"]').trigger("click");

    const sheet = document.body.querySelector('[data-test="planner-phone-mode-sheet"]');
    const seatingRow = document.body.querySelector<HTMLButtonElement>(
      '[data-test="planner-phone-mode-sheet-seating"]',
    );
    const rulesRow = document.body.querySelector<HTMLButtonElement>(
      '[data-test="planner-phone-mode-sheet-rules"]',
    );
    expect(sheet).not.toBeNull();
    expect(seatingRow?.disabled).toBe(true);
    expect(seatingRow?.title).toBe("Skapa eller välj först ett klassrum.");

    rulesRow?.click();
    await wrapper.vm.$nextTick();

    expect(wrapper.emitted("update:modeValue")).toEqual([["rules"]]);
    expect(document.body.querySelector('[data-test="planner-phone-mode-sheet"]')).toBeNull();
  });

  it("uses semantic Lucide symbols for phone workspace choices", async () => {
    const wrapper = mountTopPanel({
      modeValue: "overview",
    });

    await wrapper.get('[data-test="planner-phone-mode-sheet-trigger"]').trigger("click");

    const groupingRow = document.body.querySelector('[data-test="planner-phone-mode-sheet-grouping"]');
    const seatingRow = document.body.querySelector('[data-test="planner-phone-mode-sheet-seating"]');
    expect(groupingRow?.innerHTML).toContain("lucide-users-round");
    expect(seatingRow?.innerHTML).toContain("lucide-armchair");
    expect(seatingRow?.innerHTML).not.toContain("lucide-presentation");
  });
});
