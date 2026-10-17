import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import EditorInputSchemaPanel from "./EditorInputSchemaPanel.vue";

function mountPanel(isReadOnly = false) {
  return mount(EditorInputSchemaPanel, {
    props: {
      inputSchemaText: '[{"name":"existing"}]',
      inputSchemaError: null,
      schemaIssues: [],
      isReadOnly,
    },
    global: { stubs: { CodeMirrorEditor: true } },
  });
}

function buttonWithText(wrapper: ReturnType<typeof mountPanel>, text: string) {
  const button = wrapper.findAll("button").find((item) => item.text().startsWith(text));
  if (!button) throw new Error(`Missing action: ${text}`);
  return button;
}

afterEach(() => vi.restoreAllMocks());

describe("EditorInputSchemaPanel shared actions", () => {
  it("does not replace an existing schema when the preset confirmation is rejected", async () => {
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const wrapper = mountPanel();

    await buttonWithText(wrapper, "förval").trigger("click");
    expect(buttonWithText(wrapper, "förval").attributes("aria-expanded")).toBe("true");
    await wrapper.get('[role="menuitem"]').trigger("click");

    expect(confirm).toHaveBeenCalledOnce();
    expect(wrapper.emitted("update:inputSchemaText")).toBeUndefined();
    expect(wrapper.find('[role="menu"]').exists()).toBe(false);
    expect(buttonWithText(wrapper, "förval").attributes("aria-expanded")).toBe("false");
    wrapper.unmount();
  });

  it("prevents both mutation actions when read-only, without disabling disclosure", async () => {
    const wrapper = mountPanel(true);
    for (const label of ["förval", "formatera"]) {
      const button = buttonWithText(wrapper, label);
      expect(button.attributes("disabled")).toBeDefined();
      await button.trigger("click");
    }
    expect(wrapper.find('[role="menu"]').exists()).toBe(false);
    expect(wrapper.emitted("update:inputSchemaText")).toBeUndefined();

    await buttonWithText(wrapper, "Dölj").trigger("click");
    expect(buttonWithText(wrapper, "Visa").attributes("aria-expanded")).toBe("false");
    await buttonWithText(wrapper, "Visa").trigger("click");
    expect(buttonWithText(wrapper, "Dölj").attributes("aria-expanded")).toBe("true");
    wrapper.unmount();
  });
});
