import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { useAiStore } from "../../stores/ai";
import ProfileDisplay from "./ProfileDisplay.vue";

vi.mock("../../composables/useProfile", () => ({
  useProfile: () => ({ updateProfile: vi.fn() }),
}));
vi.mock("../../composables/useToast", () => ({
  useToast: () => ({ success: vi.fn(), failure: vi.fn(), warning: vi.fn() }),
}));
vi.mock("../../stores/auth", () => ({
  useAuthStore: () => ({
    aiPolicy: {
      remote_providers_enabled: true,
      completion_external_available: true,
      completion_local_available: true,
    },
    profile: { allow_remote_fallback: false, inline_completion_provider: "local" },
  }),
}));

describe("Profile AI edit lifecycle (F4)", () => {
  it.each(["save", "cancel"] as const)("closes after %s and reopens with one click", async (action) => {
    const pinia = createPinia();
    const ai = useAiStore(pinia);
    const persist = vi.spyOn(ai, "persistAiSettings").mockResolvedValue({} as Awaited<ReturnType<typeof ai.persistAiSettings>>);
    const wrapper = mount(ProfileDisplay, {
      props: { profile: null, email: "teacher@example.test" },
      global: { plugins: [pinia], stubs: { ProfileExamCoursesSection: true } },
    });
    const section = wrapper.findAll("section").find(node => node.find("h3").text() === "AI-inställningar")!;
    const toggle = section.get('button[aria-label="Ändra AI-inställningar"]');
    expect(toggle.text()).toBe("");
    expect(toggle.attributes("aria-expanded")).toBe("false");
    await toggle.trigger("click");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    await section.get('input[name="remote-fallback"][value="allow"]').setValue();
    const actionButton = section.findAll("button").find(button => button.text() === (action === "save" ? "Spara ändringar" : "Avbryt"))!;
    await actionButton.trigger("click");
    await flushPromises();
    expect(section.find("fieldset").exists()).toBe(false);
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(persist).toHaveBeenCalledTimes(action === "save" ? 1 : 0);

    await toggle.trigger("click");
    expect(section.find("fieldset").exists()).toBe(true);
    expect(toggle.attributes("aria-expanded")).toBe("true");
    // A reopened draft is initialized from persisted settings, not the discarded edit.
    expect((section.get('input[name="remote-fallback"][value="deny"]').element as HTMLInputElement).checked).toBe(true);
    wrapper.unmount();
  });
});
