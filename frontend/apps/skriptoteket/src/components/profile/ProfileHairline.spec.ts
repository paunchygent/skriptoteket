import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import ProfileAiSettingsInline from "./ProfileAiSettingsInline.vue";
import ProfileDisplay from "./ProfileDisplay.vue";
import ProfileEditAiSettings from "./ProfileEditAiSettings.vue";

vi.mock("../../composables/useProfile", () => ({
  useProfile: () => ({ updateProfile: vi.fn() }),
}));
vi.mock("../../composables/useToast", () => ({
  useToast: () => ({ success: vi.fn(), failure: vi.fn(), warning: vi.fn() }),
}));
vi.mock("../../stores/auth", () => ({
  useAuthStore: () => ({
    aiPolicy: {
      remote_providers_enabled: false,
      completion_external_available: false,
      completion_local_available: true,
    },
    profile: { allow_remote_fallback: false, inline_completion_provider: "local" },
  }),
}));

const hairlineBorder = ["border", "border-[var(--huleedu-panel-border)]"];
const restriction = "Systemadministratören tillåter inte externa AI-modeller";

describe("Profile hairline surfaces (F1)", () => {
  it("uses shared hairline borders for every personal editor instead of input-inline", async () => {
    const wrapper = mount(ProfileDisplay, {
      props: { profile: null, email: "teacher@example.test" },
      global: { stubs: { ProfileExamCoursesSection: true, ProfileAiSettingsInline: true } },
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

  it("uses a shared hairline for the inline administrator notice", () => {
    const wrapper = mount(ProfileAiSettingsInline, { global: { plugins: [createPinia()] } });
    const notice = wrapper.findAll("div").find(node => node.text().startsWith(restriction) && node.findAll("div").length === 0)!;
    expect(notice.classes()).toEqual(expect.arrayContaining(hairlineBorder));
    expect(notice.classes()).not.toContain("panel-inset-canvas");
    wrapper.unmount();
  });

  it("uses shared hairlines for both AI edit notices", () => {
    const wrapper = mount(ProfileEditAiSettings, { global: { plugins: [createPinia()] } });
    const notices = wrapper.findAll("div").filter(node =>
      node.findAll("div").length === 0 &&
      (node.text().startsWith(restriction) || node.text().startsWith("Externa AI-API:er kan skicka")),
    );
    expect(notices).toHaveLength(2);
    for (const notice of notices) {
      expect(notice.classes()).toEqual(expect.arrayContaining(hairlineBorder));
      expect(notice.classes()).not.toContain("panel-inset-canvas");
    }
    wrapper.unmount();
  });
});
