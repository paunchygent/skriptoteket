/**
 * Auth-entry navigation helper tests.
 *
 * These tests keep the `/auth/login` redirect contract durable and prevent
 * malformed or looping `next` values from reintroducing modal-era behavior.
 */

import { beforeEach, describe, expect, it } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import {
  buildLandingAuthEntryLocation,
  isAuthEntryPath,
  readAuthContinuation,
  resolveAuthLoginSuccessLocation,
  sanitizeAuthNextPath,
} from "./authEntryNavigation";

describe("authEntryNavigation", () => {
  beforeEach(() => {
    window.history.replaceState(null, "");
  });

  it("drops malformed and looping next values", () => {
    expect(sanitizeAuthNextPath("https://example.com/phish")).toBeNull();
    expect(sanitizeAuthNextPath("//example.com/phish")).toBeNull();
    expect(sanitizeAuthNextPath("/auth/login")).toBeNull();
    expect(sanitizeAuthNextPath("/auth/callback")).toBeNull();
    expect(sanitizeAuthNextPath("/login")).toBeNull();
    expect(sanitizeAuthNextPath("/browse?profession=svenska")).toBe("/browse?profession=svenska");
  });

  it("treats login and callback as the auth-entry surface", () => {
    expect(isAuthEntryPath("/auth/login")).toBe(true);
    expect(isAuthEntryPath("/auth/callback")).toBe(true);
    expect(isAuthEntryPath("/auth/callback/extra")).toBe(false);
  });

  it("preserves same-origin route search and hash details", () => {
    expect(sanitizeAuthNextPath("/editor?draft=head#debug")).toBe("/editor?draft=head#debug");
    expect(
      readAuthContinuation(
        {
          next: "/admin/tools?status=draft#review",
          state: "ignored-provider-return-param",
        },
        null,
      ),
    ).toEqual({
      nextPath: "/admin/tools?status=draft#review",
      classroomPlannerEntryOrigin: null,
    });
  });

  it("builds the public-app landing handoff onto auth-login", () => {
    expect(
      buildLandingAuthEntryLocation({
        name: "public-app-detail",
        params: { appId: "classroom.group-seating-studio" },
      }),
    ).toEqual({
      name: "auth-login",
      query: { next: "/apps/classroom.group-seating-studio" },
    });
  });

  it("reconstructs the classroom planner success target from route state", () => {
    window.history.replaceState({ classroomPlannerEntryOrigin: "dashboard" }, "");

    expect(
      resolveAuthLoginSuccessLocation(
        {
          nextPath: "/apps/classroom.group-seating-studio",
        },
        window.history.state,
      ),
    ).toEqual({
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("preserves query and hash when Vue Router normalizes auth success", async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/", component: { template: "<div />" } },
        { path: "/admin/tools", component: { template: "<div />" } },
      ],
    });

    await router.push("/");
    await router.push(
      resolveAuthLoginSuccessLocation(
        {
          nextPath: "/admin/tools?status=draft#review",
        },
        null,
      ),
    );

    expect(router.currentRoute.value.fullPath).toBe("/admin/tools?status=draft#review");
  });

  it("keeps classroom-planner origin in the route contract across auth detours", () => {
    expect(
      readAuthContinuation(
        {
          next: "/apps/classroom.group-seating-studio",
          classroomPlannerEntryOrigin: "dashboard",
        },
        null,
      ),
    ).toEqual({
      nextPath: "/apps/classroom.group-seating-studio",
      classroomPlannerEntryOrigin: "dashboard",
    });
  });
});
