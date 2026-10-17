/** Disclosure semantics and accessible ownership survive glyph migration. */
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { UiGlyph } from "./shared";
import UiDenseMenuButton from "./UiDenseMenuButton.vue";

describe("UiDenseMenuButton glyph contract", () => {
  it("keeps the action named and the shared menu disclosure decorative across expansion", async () => {
    const onClick = vi.fn();
    const wrapper = mount(UiDenseMenuButton, {
      props: { label: "Öppna verktyg", expanded: false },
      attrs: { onClick },
    });
    const button = wrapper.get("button");
    const glyph = wrapper.getComponent(UiGlyph);

    expect(button.text()).toBe("Öppna verktyg");
    expect(button.attributes("aria-label")).toBeUndefined();
    expect(button.attributes("aria-haspopup")).toBe("menu");
    expect(button.attributes("aria-expanded")).toBe("false");
    expect(glyph.props("meaning")).toBe("open-list");
    expect(glyph.get("svg").attributes("aria-hidden")).toBe("true");
    expect(glyph.attributes("aria-label")).toBeUndefined();
    await button.trigger("click");
    expect(onClick).toHaveBeenCalledTimes(1);

    await wrapper.setProps({ expanded: true, disabled: true });
    expect(button.attributes("aria-expanded")).toBe("true");
    expect(glyph.props("meaning")).toBe("open-list");
    await button.trigger("click");
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
