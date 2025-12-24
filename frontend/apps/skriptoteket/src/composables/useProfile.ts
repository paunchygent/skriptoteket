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

type ChangePasswordPayload = {
  current_password: string;
  new_password: string;
};

type ChangeEmailPayload = {
  email: string;
};

type ChangeEmailResponse = {
  user: ApiUser;
};

export function useProfile() {
  const auth = useAuthStore();
  const profile = ref<UserProfile | null>(null);

  async function load(): Promise<ProfileResponse> {
    const response = await apiGet<ProfileResponse>("/api/v1/profile");
    profile.value = response.profile;
    auth.user = response.user;
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
    return response;
  }

  async function changePassword(payload: ChangePasswordPayload): Promise<void> {
    await apiFetch<void>("/api/v1/profile/password", {
      method: "POST",
      body: payload,
    });
  }

  async function changeEmail(payload: ChangeEmailPayload): Promise<ApiUser> {
    const response = await apiFetch<ChangeEmailResponse>("/api/v1/profile/email", {
      method: "PATCH",
      body: payload,
    });
    auth.user = response.user;
    return response.user;
  }

  return {
    profile,
    load,
    updateProfile,
    changePassword,
    changeEmail,
  };
}
