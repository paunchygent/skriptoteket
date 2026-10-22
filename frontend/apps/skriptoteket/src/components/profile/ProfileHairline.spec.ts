import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import ProfileDisplay from "./ProfileDisplay.vue";

vi.mock("../../composables/useProfile", () => ({
  useProfile: () => ({ updateProfile: vi.fn() }),
}));
vi.mock("../../composables/useToast", () => ({
  useToast: () => ({ success: vi.fn(), failure: vi.fn(), warning: vi.fn() }),
}));

const hairlineBorder = ["border", "border-[var(--huleedu-panel-border)]"];

describe("Profile hairline surfaces (F1)", () => {
  it("uses shared hairline borders for every personal editor instead of input-inline", async () => {
    const wrapper = mount(ProfileDisplay, {
      props: { profile: null, email: "teacher@example.test" },
      global: { stubs: { ProfileExamCoursesSection: true } },
    });
    const personalSection = wrapper.findAll("section").find(section =>
      section.find("h3").text() === "Personlig information",
    )!;
    await personalSection.get("button").trigger("click");
    const editors = personalSection.findAll("input, select");
    expect(editors).toHaveLength(4);
    for (const editor of editors) {
      expect(editor.classes()).toEqual(expect.arrayContaining(hairlineBorder));
      expect(editor.classes()).not.toContain("input-inline");
      expect(editor.classes()).not.toContain("border-2");
    }
    wrapper.unmount();
  });

  it("renders no AI-settings section or control", () => {
    const wrapper = mount(ProfileDisplay, {
      props: { profile: null, email: "teacher@example.test" },
      global: { stubs: { ProfileExamCoursesSection: true } },
    });
    expect(wrapper.text()).not.toContain("AI-inställningar");
    expect(wrapper.find('[aria-label="Ändra AI-inställningar"]').exists()).toBe(false);
    expect(wrapper.findAll("section").map(section => section.find("h3").text())).toEqual([
      "Personlig information",
      "Konto",
      "Mina kurser",
    ]);
    wrapper.unmount();
  });
});
