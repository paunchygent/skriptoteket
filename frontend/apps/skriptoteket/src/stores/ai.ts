import { defineStore } from "pinia";
import { ref } from "vue";

const REMOTE_FALLBACK_STORAGE_PREFIX = "skriptoteket:ai:allow_remote_fallback";

function remoteFallbackStorageKey(userId: string): string {
  return `${REMOTE_FALLBACK_STORAGE_PREFIX}:${userId}`;
}

export const useAiStore = defineStore("ai", () => {
  const allowRemoteFallback = ref(false);
  const activeUserId = ref<string | null>(null);

  function hydrateForUser(userId: string | null): void {
    activeUserId.value = userId;
    if (!userId) {
      allowRemoteFallback.value = false;
      return;
    }

    const stored = localStorage.getItem(remoteFallbackStorageKey(userId));
    allowRemoteFallback.value = stored === "1";
  }

  function persist(): void {
    if (!activeUserId.value) {
      return;
    }
    localStorage.setItem(
      remoteFallbackStorageKey(activeUserId.value),
      allowRemoteFallback.value ? "1" : "0",
    );
  }

  function setAllowRemoteFallback(value: boolean): void {
    allowRemoteFallback.value = value;
    persist();
  }

  function enableRemoteFallback(): void {
    setAllowRemoteFallback(true);
  }

  function disableRemoteFallback(): void {
    setAllowRemoteFallback(false);
  }

  return {
    allowRemoteFallback,
    activeUserId,
    hydrateForUser,
    setAllowRemoteFallback,
    enableRemoteFallback,
    disableRemoteFallback,
  };
});
