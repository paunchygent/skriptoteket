import { defineStore } from "pinia";
import { ref, type Ref } from "vue";

/**
 * Signed-in shell modes, persisted per user.
 *
 * - `focusMode` hides the sidebar at every width and keeps the top bar.
 * - `sidebarCollapsed` collapses the desktop sidebar to the glyph rail; below
 *   1280 px the shell CSS shows the rail whatever this value is.
 */

const FOCUS_MODE_STORAGE_PREFIX = "skriptoteket:layout:focus_mode";
const SIDEBAR_COLLAPSED_STORAGE_PREFIX = "skriptoteket:layout:sidebar_collapsed";

function storageKey(prefix: string, userId: string): string {
  return `${prefix}:${userId}`;
}

/** Storage is a convenience; an unreadable value reads as the default. */
function readFlag(prefix: string, userId: string): boolean {
  try {
    return localStorage.getItem(storageKey(prefix, userId)) === "1";
  } catch {
    return false;
  }
}

/** Storage is a convenience; a failed write leaves the in-memory state. */
function writeFlag(prefix: string, userId: string, value: boolean): void {
  try {
    localStorage.setItem(storageKey(prefix, userId), value ? "1" : "0");
  } catch {
    // Storage can be full or blocked; the in-memory state still holds this visit.
  }
}

export const useLayoutStore = defineStore("layout", () => {
  const focusMode = ref(false);
  const sidebarCollapsed = ref(false);
  const activeUserId = ref<string | null>(null);

  function hydrateForUser(userId: string | null): void {
    activeUserId.value = userId;
    if (!userId) {
      focusMode.value = false;
      sidebarCollapsed.value = false;
      return;
    }

    focusMode.value = readFlag(FOCUS_MODE_STORAGE_PREFIX, userId);
    sidebarCollapsed.value = readFlag(SIDEBAR_COLLAPSED_STORAGE_PREFIX, userId);
  }

  function persist(prefix: string, value: boolean): void {
    if (!activeUserId.value) {
      return;
    }
    writeFlag(prefix, activeUserId.value, value);
  }

  function setPersisted(state: Ref<boolean>, prefix: string, value: boolean): void {
    state.value = value;
    persist(prefix, value);
  }

  function setFocusMode(value: boolean): void {
    setPersisted(focusMode, FOCUS_MODE_STORAGE_PREFIX, value);
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

  function setSidebarCollapsed(value: boolean): void {
    setPersisted(sidebarCollapsed, SIDEBAR_COLLAPSED_STORAGE_PREFIX, value);
  }

  function toggleSidebarCollapsed(): void {
    setSidebarCollapsed(!sidebarCollapsed.value);
  }

  return {
    focusMode,
    sidebarCollapsed,
    activeUserId,
    hydrateForUser,
    setFocusMode,
    enable,
    disable,
    toggle,
    setSidebarCollapsed,
    toggleSidebarCollapsed,
  };
});
