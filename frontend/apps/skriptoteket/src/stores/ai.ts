import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { apiFetch } from "../api/client";

const REMOTE_FALLBACK_STORAGE_PREFIX = "skriptoteket:ai:allow_remote_fallback";

function remoteFallbackStorageKey(userId: string): string {
  return `${REMOTE_FALLBACK_STORAGE_PREFIX}:${userId}`;
}

export type RemoteFallbackPreference = "unset" | "allow" | "deny";

type AiSettingsPayload = {
  remote_fallback_preference: RemoteFallbackPreference;
};

type HydrateAiParams = {
  userId: string | null;
  serverAllowRemoteFallback: boolean | null | undefined;
};

export const useAiStore = defineStore("ai", () => {
  const remoteFallbackPreference = ref<RemoteFallbackPreference>("unset");
  const activeUserId = ref<string | null>(null);

  const allowRemoteFallback = computed(() => remoteFallbackPreference.value === "allow");

  function preferenceFromServer(value: boolean | null | undefined): RemoteFallbackPreference {
    if (value === true) return "allow";
    if (value === false) return "deny";
    return "unset";
  }

  function preferenceFromStorage(userId: string): RemoteFallbackPreference {
    const stored = localStorage.getItem(remoteFallbackStorageKey(userId));
    if (stored === "1") {
      return "allow";
    }

    if (stored === "0") {
      return "deny";
    }

    return "unset";
  }

  function clearMigrationStorage(userId: string): void {
    localStorage.removeItem(remoteFallbackStorageKey(userId));
  }

  async function persistRemoteFallbackPreference(value: RemoteFallbackPreference): Promise<void> {
    if (!activeUserId.value) {
      remoteFallbackPreference.value = value;
      return;
    }

    await apiFetch("/api/v1/profile/ai-settings", {
      method: "PATCH",
      body: { remote_fallback_preference: value } satisfies AiSettingsPayload,
    });

    clearMigrationStorage(activeUserId.value);
  }

  function hydrateForUser(params: HydrateAiParams): void {
    activeUserId.value = params.userId;
    if (!params.userId) {
      remoteFallbackPreference.value = "unset";
      return;
    }

    const serverPreference = preferenceFromServer(params.serverAllowRemoteFallback);
    if (serverPreference !== "unset") {
      remoteFallbackPreference.value = serverPreference;
      clearMigrationStorage(params.userId);
      return;
    }

    const storedPreference = preferenceFromStorage(params.userId);
    remoteFallbackPreference.value = storedPreference;

    if (storedPreference !== "unset") {
      void persistRemoteFallbackPreference(storedPreference).catch(() => {
        // keep the local migration key so we can retry later
      });
    }
  }

  function setRemoteFallbackPreference(value: RemoteFallbackPreference): void {
    remoteFallbackPreference.value = value;
  }

  function setAllowRemoteFallback(value: boolean): void {
    setRemoteFallbackPreference(value ? "allow" : "deny");
  }

  function enableRemoteFallback(): void {
    setAllowRemoteFallback(true);
  }

  function disableRemoteFallback(): void {
    setAllowRemoteFallback(false);
  }

  return {
    allowRemoteFallback,
    remoteFallbackPreference,
    activeUserId,
    hydrateForUser,
    setRemoteFallbackPreference,
    persistRemoteFallbackPreference,
    setAllowRemoteFallback,
    enableRemoteFallback,
    disableRemoteFallback,
  };
});
