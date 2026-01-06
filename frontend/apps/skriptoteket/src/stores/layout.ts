import { defineStore } from "pinia";
import { ref } from "vue";

const FOCUS_MODE_STORAGE_PREFIX = "skriptoteket:layout:focus_mode";

function focusModeStorageKey(userId: string): string {
  return `${FOCUS_MODE_STORAGE_PREFIX}:${userId}`;
}

export const useLayoutStore = defineStore("layout", () => {
  const focusMode = ref(false);
  const activeUserId = ref<string | null>(null);

  function hydrateForUser(userId: string | null): void {
    activeUserId.value = userId;
    if (!userId) {
      focusMode.value = false;
      return;
    }

    const stored = localStorage.getItem(focusModeStorageKey(userId));
    focusMode.value = stored === "1";
  }

  function persist(): void {
    if (!activeUserId.value) {
      return;
    }
    localStorage.setItem(
      focusModeStorageKey(activeUserId.value),
      focusMode.value ? "1" : "0",
    );
  }

  function setFocusMode(value: boolean): void {
    focusMode.value = value;
    persist();
  }

  function enable(): void {
    setFocusMode(true);
  }

  function disable(): void {
    setFocusMode(false);
  }

  function toggle(): void {
    setFocusMode(!focusMode.value);
  }

  return {
    focusMode,
    activeUserId,
    hydrateForUser,
    setFocusMode,
    enable,
    disable,
    toggle,
  };
});
