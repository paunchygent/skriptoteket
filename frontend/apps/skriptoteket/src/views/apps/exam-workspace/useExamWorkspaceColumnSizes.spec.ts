/**
 * Exam workspace column sizes state.
 *
 * Expected behavior:
 *   The composable reads the remembered widths once on setup. `setWidth`
 *   rounds to an integer and persists without clamping; `resetWidth` deletes
 *   that column's stored width; `toggleListCollapsed` flips and persists the
 *   flag (default false). `rootStyle` holds only stored widths as inline
 *   custom properties, so a missing width writes nothing and CSS defaults
 *   apply. With throwing storage the composable still works in memory.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { useExamWorkspaceColumnSizes } from "./useExamWorkspaceColumnSizes";
import {
  readExamWorkspaceColumnSizes,
  writeExamWorkspaceColumnSizes,
} from "./examWorkspaceColumnSizesStorage";

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("useExamWorkspaceColumnSizes", () => {
  it("restores a stored width on setup and exposes it in rootStyle", () => {
    writeExamWorkspaceColumnSizes({ list: 280 });

    const state = useExamWorkspaceColumnSizes();

    expect(state.sizes.value.list).toBe(280);
    expect(state.rootStyle.value).toEqual({ "--xw-list-size": "280px" });
  });

  it("starts with empty sizes, no collapsed flag and no rootStyle entries", () => {
    const state = useExamWorkspaceColumnSizes();

    expect(state.sizes.value).toEqual({});
    expect(state.listCollapsed.value).toBe(false);
    expect(state.rootStyle.value).toEqual({});
  });

  it("persists setWidth rounded to an integer and updates rootStyle", () => {
    const state = useExamWorkspaceColumnSizes();

    state.setWidth("drawer", 321.6);

    expect(state.sizes.value.drawer).toBe(322);
    expect(state.rootStyle.value).toEqual({ "--xw-drawer-size": "322px" });
    expect(readExamWorkspaceColumnSizes()).toEqual({ drawer: 322 });
  });

  it("removes the width from storage and rootStyle on resetWidth", () => {
    writeExamWorkspaceColumnSizes({ preview: 500, list: 280 });
    const state = useExamWorkspaceColumnSizes();

    state.resetWidth("preview");

    expect(state.sizes.value.preview).toBeUndefined();
    expect(state.rootStyle.value).toEqual({ "--xw-list-size": "280px" });
  });

  it("persists the collapsed flag on toggleListCollapsed", () => {
    const state = useExamWorkspaceColumnSizes();

    state.toggleListCollapsed();
    expect(state.listCollapsed.value).toBe(true);

    const restored = useExamWorkspaceColumnSizes();
    expect(restored.listCollapsed.value).toBe(true);

    state.toggleListCollapsed();
    expect(useExamWorkspaceColumnSizes().listCollapsed.value).toBe(false);
  });

  it("keeps working in memory when storage throws", () => {
    vi.spyOn(localStorage, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(localStorage, "setItem").mockImplementation(() => {
      throw new Error("full");
    });

    const state = useExamWorkspaceColumnSizes();

    expect(() => state.setWidth("list", 300)).not.toThrow();
    expect(() => state.toggleListCollapsed()).not.toThrow();
    expect(state.sizes.value.list).toBe(300);
    expect(state.listCollapsed.value).toBe(true);
    expect(state.rootStyle.value).toEqual({ "--xw-list-size": "300px" });
  });
});
