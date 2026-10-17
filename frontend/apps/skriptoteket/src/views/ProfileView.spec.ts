import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import type { components } from "../api/openapi";
import ProfileView from "./ProfileView.vue";

type UserProfile = components["schemas"]["UserProfile"];
const mocks = vi.hoisted(() => ({ load: vi.fn(), updateProfile: vi.fn() }));
const profile = ref<UserProfile | null>(null);
vi.mock("../composables/useProfile", () => ({
  useProfile: () => ({ profile, ...mocks }),
}));
vi.mock("../stores/auth", () => ({
  useAuthStore: () => ({ user: { email: "teacher@example.test" } }),
}));
vi.mock("../composables/useToast", () => ({
  useToast: () => ({ success: vi.fn(), failure: vi.fn() }),
}));

const savedProfile: UserProfile = {
  user_id: "teacher-1", first_name: "Anna", last_name: "Lärare",
  display_name: "Anna", locale: "sv-SE", exam_list_ordering: "course",
  created_at: "2026-10-17T10:00:00Z", updated_at: "2026-10-17T10:00:00Z",
};

function deferred() {
  let resolve!: () => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<void>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function mountProfile() {
  return mount(ProfileView, {
    global: { stubs: { ProfileExamCoursesSection: true, ProfileAiSettingsInline: true } },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  profile.value = null;
  mocks.load.mockImplementation(async () => { profile.value = { ...savedProfile }; });
  mocks.updateProfile.mockResolvedValue(undefined);
});

describe("ProfileView reload continuity", () => {
  it.each(["success", "failure"] as const)("keeps the saved card and a new draft mounted during a %s reload", async (outcome) => {
    const wrapper = mountProfile();
    await flushPromises();
    const card = wrapper.get("h2").element;
    const reload = deferred();
    mocks.load.mockReturnValueOnce(reload.promise);
    const personalSection = wrapper.findAll("section")[0]!;
    await personalSection.get("button").trigger("click");
    await wrapper.get("#edit-first-name").setValue("Eva");
    const save = personalSection.findAll("button").find(button => button.text() === "Spara ändringar")!;
    await save.trigger("click");
    await flushPromises();
    expect(mocks.updateProfile).toHaveBeenCalledWith(expect.objectContaining({ first_name: "Eva" }));
    expect(wrapper.find("h2").exists()).toBe(true);
    expect(wrapper.get("h2").element).toBe(card);

    // A second edit must survive completion (or failure) of the earlier reload.
    await wrapper.findAll("section")[0]!.get("button").trigger("click");
    await wrapper.get("#edit-first-name").setValue("Oavslutat utkast");
    const draftInput = wrapper.get("#edit-first-name").element;
    if (outcome === "failure") reload.reject(new Error("Servern svarar inte"));
    else {
      profile.value = { ...savedProfile, first_name: "Eva" };
      reload.resolve();
    }
    await flushPromises();
    expect(wrapper.get("h2").element).toBe(card);
    expect(wrapper.get("#edit-first-name").element).toBe(draftInput);
    expect((draftInput as HTMLInputElement).value).toBe("Oavslutat utkast");
    if (outcome === "failure") expect(wrapper.get('[role="alert"]').text()).toContain("Servern svarar inte");
    wrapper.unmount();
  });

  it("does not display an empty profile card when the initial request fails", async () => {
    const initial = deferred();
    mocks.load.mockReturnValueOnce(initial.promise);
    const wrapper = mountProfile();
    expect(wrapper.find("h2").exists()).toBe(false);
    initial.reject(new Error("Profilen kunde inte hämtas"));
    await flushPromises();
    expect(wrapper.find("h2").exists()).toBe(false);
    expect(wrapper.get('[role="alert"]').text()).toContain("Profilen kunde inte hämtas");
    wrapper.unmount();
  });
});
