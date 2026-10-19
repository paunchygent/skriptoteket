import { beforeEach, describe, expect, it, vi } from "vitest";
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

  it("keeps the rail per user and apart from focus mode", () => {
    const railKey = (userId: string): string => `skriptoteket:layout:sidebar_collapsed:${userId}`;
    localStorage.setItem(railKey("teacher-a"), "1");

    const store = useLayoutStore();
    store.hydrateForUser("teacher-a");
    expect(store.sidebarCollapsed).toBe(true);
    expect(store.focusMode).toBe(false);

    store.toggle();
    expect(store.sidebarCollapsed).toBe(true);
    expect(localStorage.getItem(railKey("teacher-a"))).toBe("1");

    store.hydrateForUser("teacher-b");
    expect(store.sidebarCollapsed).toBe(false);

    store.toggleSidebarCollapsed();
    expect(localStorage.getItem(railKey("teacher-b"))).toBe("1");
    expect(localStorage.getItem(storageKey("teacher-b"))).toBeNull();

    store.hydrateForUser(null);
    expect(store.sidebarCollapsed).toBe(false);

    store.toggleSidebarCollapsed();
    expect(localStorage.getItem(railKey("null"))).toBeNull();
    expect(localStorage.length).toBe(3);
  });

  it("stays at the defaults when getItem throws", () => {
    const store = useLayoutStore();
    const getItem = vi.spyOn(localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });

    try {
      expect(() => store.hydrateForUser("user-9")).not.toThrow();
      expect(store.focusMode).toBe(false);
      expect(store.sidebarCollapsed).toBe(false);
    } finally {
      getItem.mockRestore();
    }
  });

  it("does not throw when setItem throws", () => {
    const store = useLayoutStore();
    store.hydrateForUser("user-9");
    const setItem = vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new Error("full");
    });

    try {
      expect(() => store.enable()).not.toThrow();
      expect(() => store.toggleSidebarCollapsed()).not.toThrow();
      expect(store.focusMode).toBe(true);
      expect(store.sidebarCollapsed).toBe(true);
    } finally {
      setItem.mockRestore();
    }
  });
});
