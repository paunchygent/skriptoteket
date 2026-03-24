/**
 * Classroom planner navigation helper tests.
 *
 * These tests lock down the entry-origin contract used by the landing-page
 * cutover so launch links, reload fallback, and `Avsluta` routing stay small
 * and predictable.
 */

import { describe, expect, it } from "vitest";

import {
  buildClassroomPlannerEntryTarget,
  CLASSROOM_PLANNER_APP_ID,
  isReloadNavigation,
  readClassroomPlannerEntryOriginFromHistoryState,
  resolveClassroomPlannerEntryOriginFromRouteName,
  resolveClassroomPlannerExitTarget,
} from "./classroomPlannerNavigation";

describe("classroomPlannerNavigation", () => {
  it("maps dashboard and browse routes to the supported entry origins", () => {
    expect(resolveClassroomPlannerEntryOriginFromRouteName("home")).toBe("dashboard");
    expect(resolveClassroomPlannerEntryOriginFromRouteName("browse")).toBe("catalog");
    expect(resolveClassroomPlannerEntryOriginFromRouteName("browse-tools")).toBe("catalog");
    expect(resolveClassroomPlannerEntryOriginFromRouteName("profile")).toBeNull();
  });

  it("builds a classroom-planner app target with history state when origin is known", () => {
    expect(buildClassroomPlannerEntryTarget("dashboard")).toEqual({
      name: "app-detail",
      params: { appId: CLASSROOM_PLANNER_APP_ID },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("reads the entry origin from history state and ignores invalid values", () => {
    expect(
      readClassroomPlannerEntryOriginFromHistoryState({
        classroomPlannerEntryOrigin: "catalog",
      }),
    ).toBe("catalog");
    expect(readClassroomPlannerEntryOriginFromHistoryState({ classroomPlannerEntryOrigin: "else" })).toBeNull();
    expect(readClassroomPlannerEntryOriginFromHistoryState(null)).toBeNull();
  });

  it("falls back to the catalog exit target when no trusted origin exists", () => {
    expect(resolveClassroomPlannerExitTarget("dashboard")).toEqual({ name: "home" });
    expect(resolveClassroomPlannerExitTarget("catalog")).toEqual({ name: "browse" });
    expect(resolveClassroomPlannerExitTarget(null)).toEqual({ name: "browse" });
  });

  it("treats navigation reloads as untrusted for exit restoration", () => {
    expect(isReloadNavigation([{ type: "reload" }])).toBe(true);
    expect(isReloadNavigation([{ type: "navigate" }])).toBe(false);
    expect(isReloadNavigation([])).toBe(false);
  });
});
