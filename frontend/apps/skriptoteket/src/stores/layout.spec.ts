import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useLayoutStore } from "./layout";

const storageKey = (userId: string): string => `skriptoteket:layout:focus_mode:${userId}`;

describe("useLayoutStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  it("starts with focus mode disabled", () => {
    const store = useLayoutStore();

    expect(store.focusMode).toBe(false);
    expect(store.activeUserId).toBeNull();
  });

  it("hydrates from localStorage per user", () => {
    localStorage.setItem(storageKey("user-1"), "1");
    localStorage.setItem(storageKey("user-2"), "0");

    const store = useLayoutStore();

    store.hydrateForUser("user-1");
    expect(store.focusMode).toBe(true);
    expect(store.activeUserId).toBe("user-1");

    store.hydrateForUser("user-2");
    expect(store.focusMode).toBe(false);
    expect(store.activeUserId).toBe("user-2");
  });

  it("persists focus mode changes for the active user", () => {
    const store = useLayoutStore();

    store.hydrateForUser("user-3");
    store.enable();
    expect(localStorage.getItem(storageKey("user-3"))).toBe("1");

    store.disable();
    expect(localStorage.getItem(storageKey("user-3"))).toBe("0");
  });

  it("does not leak focus mode between users", () => {
    localStorage.setItem(storageKey("teacher-a"), "1");

    const store = useLayoutStore();
    store.hydrateForUser("teacher-a");
    expect(store.focusMode).toBe(true);

    store.hydrateForUser("teacher-b");
    expect(store.focusMode).toBe(false);

    store.enable();
    expect(localStorage.getItem(storageKey("teacher-a"))).toBe("1");
    expect(localStorage.getItem(storageKey("teacher-b"))).toBe("1");
  });

  it("clears focus mode when no user is active", () => {
    const store = useLayoutStore();
    store.hydrateForUser("user-4");
    store.enable();

    store.hydrateForUser(null);
    expect(store.focusMode).toBe(false);
    expect(store.activeUserId).toBeNull();
  });
});
