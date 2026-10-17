import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ProfileInlineField from "./ProfileInlineField.vue";

describe("ProfileInlineField", () => {
  it("names text and select editors through their own visible field labels", async () => {
    const wrapper = mount({
      components: { ProfileInlineField },
      template: `<dl>
        <ProfileInlineField label="Förnamn" value="Anna" />
        <ProfileInlineField label="Språk" value="sv-SE" type="select" :options="[{ value: 'sv-SE', label: 'Svenska' }]" />
      </dl>`,
    });
    for (const button of wrapper.findAll("button")) await button.trigger("click");
    const labelIds: string[] = [];
    for (const [index, editor] of wrapper.findAll("input, select").entries()) {
      const labelId = editor.attributes("aria-labelledby");
      expect(labelId).toBeTruthy();
      labelIds.push(labelId!);
      const label = wrapper.get(`[id="${labelId}"]`);
      expect(label.element.tagName).toBe("DT");
      expect(label.text()).toBe(index === 0 ? "Förnamn" : "Språk");
    }
    expect(labelIds).toHaveLength(2);
    expect(new Set(labelIds).size).toBe(2);
    wrapper.unmount();
  });

  it("focuses the text editor, discards Escape changes, and submits only the subsequent draft", async () => {
    const wrapper = mount(ProfileInlineField, {
      attachTo: document.body,
      props: { label: "Förnamn", value: "Anna" },
    });
    try {
      await wrapper.get("button").trigger("click");
      const input = wrapper.get<HTMLInputElement>("input");
      expect(document.activeElement).toBe(input.element);
      await input.setValue("Ska inte sparas");
      await input.trigger("keydown", { key: "Escape" });
      expect(wrapper.find("input").exists()).toBe(false);
      expect(wrapper.emitted("save")).toBeUndefined();
      expect(wrapper.emitted("cancel")).toHaveLength(1);
      expect(wrapper.text()).toContain("Anna");
      await wrapper.get("button").trigger("click");
      expect(wrapper.get<HTMLInputElement>("input").element.value).toBe("Anna");
      await wrapper.get("input").setValue("Eva");
      await wrapper.get("input").trigger("keydown", { key: "Enter" });
      expect(wrapper.emitted("save")).toEqual([["Eva"]]);
      await wrapper.setProps({ saving: true });
      expect(wrapper.get<HTMLInputElement>("input").element.disabled).toBe(true);
      expect(wrapper.findAll("button").every(button => (button.element as HTMLButtonElement).disabled)).toBe(true);
      await wrapper.get("input").trigger("keydown", { key: "Enter" });
      expect(wrapper.emitted("save")).toHaveLength(1);
      await wrapper.setProps({ saving: false, value: "Eva" });
      expect(wrapper.find("input").exists()).toBe(false);
      expect(wrapper.text()).toContain("Eva");
    } finally {
      wrapper.unmount();
    }
  });

  it("does not submit a select on Enter and emits its chosen value only through Save", async () => {
    const wrapper = mount(ProfileInlineField, {
      props: {
        label: "Språk", value: "sv-SE", type: "select",
        options: [{ value: "sv-SE", label: "Svenska" }, { value: "en-US", label: "English" }],
      },
    });
    await wrapper.get("button").trigger("click");
    await wrapper.get("select").setValue("en-US");
    await wrapper.get("select").trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("save")).toBeUndefined();
    await wrapper.findAll("button").find(button => button.text() === "Spara")!.trigger("click");
    expect(wrapper.emitted("save")).toEqual([["en-US"]]);
    wrapper.unmount();
  });
});
