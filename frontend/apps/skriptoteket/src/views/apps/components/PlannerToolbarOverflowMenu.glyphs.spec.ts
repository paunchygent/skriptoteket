/** Dynamic overflow actions retain their meaning and callback ownership. */
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { UiGlyph } from "../../../components/ui/shared";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";

describe("PlannerToolbarOverflowMenu glyph contract", () => {
  it("renders dynamic meanings decoratively in both action groups and never selects disabled actions", async () => {
    const configure = vi.fn();
    const history = vi.fn();
    const wrapper = mount(PlannerToolbarOverflowMenu, {
      props: {
        items: [
          { id: "configure", label: "Inställningar", glyph: "configure", group: "primary", testId: "configure", onSelect: configure },
          { id: "history", label: "Historik", glyph: "history", disabled: true, testId: "history", onSelect: history },
        ],
      },
    });
    const trigger = wrapper.get('button[aria-haspopup="menu"]');
    expect(trigger.attributes("aria-label")).toBe("Fler åtgärder");
    await trigger.trigger("click");
    expect(trigger.attributes("aria-expanded")).toBe("true");

    for (const meaning of ["configure", "history"] as const) {
      const item = wrapper.get(`[data-test="${meaning}"]`);
      const glyph = item.getComponent(UiGlyph);
      expect(item.attributes("role")).toBe("menuitem");
      expect(item.text()).toBe(meaning === "configure" ? "Inställningar" : "Historik");
      expect(glyph.props("meaning")).toBe(meaning);
      expect(glyph.get("svg").attributes("aria-hidden")).toBe("true");
      expect(glyph.attributes("aria-label")).toBeUndefined();
    }
    await wrapper.get('[data-test="history"]').trigger("click");
    expect(history).not.toHaveBeenCalled();
    expect(trigger.attributes("aria-expanded")).toBe("true");
    await wrapper.get('[data-test="configure"]').trigger("click");
    expect(configure).toHaveBeenCalledTimes(1);
    expect(history).not.toHaveBeenCalled();
    expect(trigger.attributes("aria-expanded")).toBe("false");
    wrapper.unmount();
  });
});
