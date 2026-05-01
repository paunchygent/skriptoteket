/**
 * Planner top-panel tests.
 *
 * These tests lock the workspace header's close affordance so it uses the
 * shared icon-button primitive while retaining the existing exit behavior.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PlannerTopPanel from "./PlannerTopPanel.vue";

function mountTopPanel() {
  return mount(PlannerTopPanel, {
    props: {
      title: "SA25D",
      contextLabel: "Sal 101",
      modeValue: "rules",
    },
  });
}

describe("PlannerTopPanel", () => {
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
});
