import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { denseStatusPillClass, UiDenseStatusPill } from "./shared";

describe("shared UiDenseStatusPill compact contract", () => {
  it.each(["neutral", "success", "warning", "error"] as const)(
    "renders a %s tone dot with an assistive-only label instead of a visible text pill",
    (tone) => {
      const wrapper = mount(UiDenseStatusPill, {
        props: { label: "Alla ändringar sparade", tone, compact: true },
      });
      const pill = wrapper.get('[data-ui="dense-status-pill"]');
      const label = pill.get(".sr-only");
      expect(label.text()).toBe("Alla ändringar sparade");
      expect(label.attributes("aria-hidden")).not.toBe("true");
      expect(label.element.closest('[aria-hidden="true"]')).toBeNull();
      // sr-only is visually hidden, not removed from the accessibility tree.
      expect(label.classes()).not.toContain("hidden");
      const dot = pill.get('[aria-hidden="true"]');
      expect(dot.text()).toBe("");
      expect(dot.classes()).toEqual(expect.arrayContaining(["h-2", "w-2", "bg-current"]));
      const toneClass = { neutral: "text-navy/70", success: "text-success", warning: "text-warning", error: "text-error" }[tone];
      expect(pill.classes()).toContain(toneClass);
      expect(pill.classes()).toEqual(expect.arrayContaining(["h-3", "w-3"]));
      expect(pill.classes()).not.toContain("h-[28px]");
      const helperClasses = denseStatusPillClass({ compact: true, tone }).split(/\s+/);
      expect(helperClasses).toEqual(expect.arrayContaining(["h-3", "w-3", toneClass]));
      expect(helperClasses).not.toContain("h-[28px]");
      const visibleContent = pill.element.cloneNode(true) as HTMLElement;
      visibleContent.querySelectorAll(".sr-only").forEach((node) => node.remove());
      expect(visibleContent.textContent?.trim()).toBe("");
      wrapper.unmount();
    },
  );

  it("keeps the default pill's visible label and 28px height without adding a dot", () => {
    const wrapper = mount(UiDenseStatusPill, { props: { label: "Sparat", tone: "success" } });
    const pill = wrapper.get('[data-ui="dense-status-pill"]');
    expect(pill.text()).toBe("Sparat");
    expect(pill.classes()).toContain("h-[28px]");
    expect(pill.find(".sr-only").exists()).toBe(false);
    expect(pill.find('[aria-hidden="true"]').exists()).toBe(false);
    expect(denseStatusPillClass()).toBe(denseStatusPillClass({ compact: false }));
    wrapper.unmount();
  });
});
