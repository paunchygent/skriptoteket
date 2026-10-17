/** Selection is a control state, not an independent image or confirmation. */
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { UiGlyph } from "./shared";
import UiDenseToggle from "./UiDenseToggle.vue";

describe("UiDenseToggle glyph contract", () => {
  it("keeps the selected glyph decorative while the switch owns its name and state", async () => {
    const wrapper = mount(UiDenseToggle, {
      props: { modelValue: false, label: "Smart", ariaLabel: "Smart fördelning" },
    });
    const control = wrapper.get('[role="switch"]');
    const glyph = wrapper.getComponent(UiGlyph);
    expect(control.attributes("aria-label")).toBe("Smart fördelning");
    expect(control.attributes("aria-checked")).toBe("false");
    expect(glyph.props("meaning")).toBe("selected");
    expect(glyph.get("svg").attributes("aria-hidden")).toBe("true");
    expect(glyph.attributes("aria-label")).toBeUndefined();
    await control.trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([[true]]);
    await wrapper.setProps({ modelValue: true });
    expect(control.attributes("aria-checked")).toBe("true");
    await control.trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([[true], [false]]);
    await wrapper.setProps({ disabled: true });
    await control.trigger("click");
    expect(wrapper.emitted("update:modelValue")).toHaveLength(2);
  });
});
