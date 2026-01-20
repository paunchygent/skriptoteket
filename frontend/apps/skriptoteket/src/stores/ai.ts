import { defineStore } from "pinia";
import { computed } from "vue";

import { apiFetch } from "../api/client";
import type { components } from "../api/openapi";
import { useAuthStore } from "./auth";

export type RemoteFallbackPreference = "unset" | "allow" | "deny";
export type InlineCompletionProviderPreference = "unset" | "local" | "external";

type ProfileResponse = components["schemas"]["ProfileResponse"];

type AiSettingsPayload = components["schemas"]["UpdateAiSettingsRequest"];

const REMOTE_FALLBACK_REQUIRED_CODE = "remote_fallback_required";
const NOTICE_STORAGE_PREFIX = "skriptoteket:notice:last_seen";
const REMOTE_FALLBACK_NOTICE_TTL_MS = 24 * 60 * 60 * 1000;

function noticeStorageKey(params: { userId: string; code: string }): string {
  return `${NOTICE_STORAGE_PREFIX}:${params.userId}:${params.code}`;
}

export const useAiStore = defineStore("ai", () => {
  const auth = useAuthStore();

  const remoteProvidersEnabled = computed(
    () => auth.aiPolicy?.remote_providers_enabled ?? true,
  );
  const completionExternalAvailable = computed(
    () => auth.aiPolicy?.completion_external_available ?? false,
  );
  const completionLocalAvailable = computed(
    () => auth.aiPolicy?.completion_local_available ?? false,
  );

  const remoteFallbackPreference = computed<RemoteFallbackPreference>(() => {
    const value = auth.profile?.allow_remote_fallback;
    if (value === true) return "allow";
    if (value === false) return "deny";
    return "unset";
  });

  const inlineCompletionProviderPreference = computed<InlineCompletionProviderPreference>(() => {
    const value = auth.profile?.inline_completion_provider;
    if (value === "local") return "local";
    if (value === "external") return "external";
    return "unset";
  });

  const allowRemoteFallback = computed(() => remoteFallbackPreference.value === "allow");
  const allowRemoteProviders = computed(
    () => remoteProvidersEnabled.value && allowRemoteFallback.value,
  );

  async function persistAiSettings(payload: AiSettingsPayload): Promise<ProfileResponse> {
    const response = await apiFetch<ProfileResponse>("/api/v1/profile/ai-settings", {
      method: "PATCH",
      body: payload satisfies AiSettingsPayload,
    });

    auth.user = response.user;
    auth.profile = response.profile;
    return response;
  }

  async function persistRemoteFallbackPreference(value: RemoteFallbackPreference): Promise<void> {
    await persistAiSettings({ remote_fallback_preference: value });
  }

  async function persistInlineCompletionProviderPreference(
    value: InlineCompletionProviderPreference,
  ): Promise<void> {
    await persistAiSettings({ inline_completion_provider_preference: value });
  }

  function shouldShowRemoteFallbackRequiredNotice(params: { code?: string | null }): boolean {
    if (params.code !== REMOTE_FALLBACK_REQUIRED_CODE) {
      return true;
    }

    const userId = auth.user?.id;
    if (!userId) {
      return true;
    }

    if (typeof window === "undefined") {
      return true;
    }

    const key = noticeStorageKey({ userId, code: REMOTE_FALLBACK_REQUIRED_CODE });
    const now = Date.now();
    const stored = window.localStorage.getItem(key);
    const lastSeen = stored ? Number(stored) : 0;
    if (Number.isFinite(lastSeen) && lastSeen > 0 && now - lastSeen < REMOTE_FALLBACK_NOTICE_TTL_MS) {
      return false;
    }

    window.localStorage.setItem(key, String(now));
    return true;
  }

  return {
    remoteProvidersEnabled,
    completionExternalAvailable,
    completionLocalAvailable,
    remoteFallbackPreference,
    inlineCompletionProviderPreference,
    allowRemoteFallback,
    allowRemoteProviders,
    persistAiSettings,
    persistRemoteFallbackPreference,
    persistInlineCompletionProviderPreference,
    shouldShowRemoteFallbackRequiredNotice,
  };
});
