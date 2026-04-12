import { ref } from "vue";

import { apiFetch, apiGet } from "../api/client";
import type { components } from "../api/openapi";
import { useAuthStore } from "../stores/auth";

type ApiUser = components["schemas"]["User"];

type UserProfile = {
  user_id: string;
  first_name: string | null;
  last_name: string | null;
  display_name: string | null;
  allow_remote_fallback?: boolean | null;
  inline_completion_provider?: "local" | "external" | null;
  locale: string;
  created_at: string;
  updated_at: string;
};

type ProfileResponse = {
  user: ApiUser;
  profile: UserProfile;
};

type UpdateProfilePayload = {
  first_name?: string | null;
  last_name?: string | null;
  display_name?: string | null;
  locale?: string | null;
};

export function useProfile() {
  const auth = useAuthStore();
  const profile = ref<UserProfile | null>(null);

  async function load(): Promise<ProfileResponse> {
    const response = await apiGet<ProfileResponse>("/api/v1/profile");
    profile.value = response.profile;
    auth.user = response.user;
    auth.profile = response.profile;
    return response;
  }

  async function updateProfile(
    payload: UpdateProfilePayload,
  ): Promise<ProfileResponse> {
    const response = await apiFetch<ProfileResponse>("/api/v1/profile", {
      method: "PATCH",
      body: payload,
    });
    profile.value = response.profile;
    auth.user = response.user;
    auth.profile = response.profile;
    return response;
  }

  return {
    profile,
    load,
    updateProfile,
  };
}
