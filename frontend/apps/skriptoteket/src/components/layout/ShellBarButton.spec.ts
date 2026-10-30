/**
 * Shell ghost-button word-visibility tests.
 *
 * The word-visibility mode is a class contract: the scoped stylesheet keys the
 * phone and desktop rules off `shell-bar-button--word-<mode>`, so the rendered
 * class must name the requested mode. Which width hides the word is proven by
 * the browser walk; these cases assert the markup that selects the rule.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ShellBarButton from "./ShellBarButton.vue";

function mountButton(props: Record<string, unknown>) {
  return mount(ShellBarButton, {
    props: {
      glyph: "help",
      label: "Hjälp",
      word: "Hjälp",
      ...props,
    },
  });
}

describe("ShellBarButton word visibility", () => {
  it("applies the tablet word mode class so the word hides below 768 px", () => {
    const button = mountButton({ wordFrom: "tablet" });

    expect(button.classes()).toContain("shell-bar-button");
    expect(button.classes()).toContain("shell-bar-button--word-tablet");
    expect(button.get(".shell-bar-button__word").text()).toBe("Hjälp");
    expect(button.attributes("aria-label")).toBe("Hjälp");
  });

  it("keeps the existing modes on their own classes", () => {
    expect(mountButton({ wordFrom: "always" }).classes()).toContain(
      "shell-bar-button--word-always",
    );
    expect(mountButton({ wordFrom: "desktop" }).classes()).toContain(
      "shell-bar-button--word-desktop",
    );
    expect(mountButton({ wordFrom: "never" }).classes()).toContain(
      "shell-bar-button--word-never",
    );
  });

  it("falls back to the glyph-only class without a word", () => {
    const button = mount(ShellBarButton, {
      props: { glyph: "help", label: "Hjälp", wordFrom: "tablet" },
    });

    expect(button.classes()).toContain("shell-bar-button--word-never");
  });
});
