import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

const mockUseAuthStore = vi.fn();
let registeredGuard: ((to: unknown, from: unknown) => Promise<unknown> | unknown) | null = null;

vi.mock("vue-router", async (importOriginal) => {
  const actual = await importOriginal<typeof import("vue-router")>();
  return {
    ...actual,
    createRouter: (options: Parameters<typeof actual.createRouter>[0]) => {
      const router = actual.createRouter(options);
      const originalBeforeEach = router.beforeEach.bind(router);
      router.beforeEach = (guard) => {
        registeredGuard = guard as (to: unknown, from: unknown) => Promise<unknown> | unknown;
        return originalBeforeEach(guard);
      };
      return router;
    },
  };
});

vi.mock("../stores/auth", () => ({
  useAuthStore: mockUseAuthStore,
}));

function createAuth(overrides?: {
  isAuthenticated?: boolean;
  hasAtLeastRole?: (role: string) => boolean;
}) {
  return {
    isAuthenticated: overrides?.isAuthenticated ?? false,
    hasAtLeastRole: overrides?.hasAtLeastRole ?? vi.fn().mockReturnValue(false),
    bootstrap: vi.fn().mockResolvedValue(undefined),
  };
}

beforeAll(async () => {
  await import("./index");
});

beforeEach(async () => {
  mockUseAuthStore.mockReset();
});

describe("router guards", () => {
  it("redirects protected routes to auth-login when the user is unauthenticated", async () => {
    const auth = createAuth();
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/browse",
      fullPath: "/browse",
      meta: { requiresAuth: true },
      query: {},
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toEqual({
      name: "auth-login",
      query: { next: "/browse" },
    });
  });

  it("does not treat /login or nearby paths as auth-entry routes", async () => {
    const auth = createAuth();
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const exactLoginResult = await guard({
      path: "/login",
      fullPath: "/login",
      meta: {},
      query: {},
    }, { name: undefined });
    const nestedLoginResult = await guard({
      path: "/login/oops",
      fullPath: "/login/oops",
      meta: {},
      query: {},
    }, { name: undefined });
    const prefixedLoginResult = await guard({
      path: "/login-foo",
      fullPath: "/login-foo",
      meta: {},
      query: {},
    }, { name: undefined });

    expect(auth.bootstrap).not.toHaveBeenCalled();
    expect(exactLoginResult).toBe(true);
    expect(nestedLoginResult).toBe(true);
    expect(prefixedLoginResult).toBe(true);
  });

  it("redirects to forbidden when minRole is not satisfied", async () => {
    const auth = createAuth({
      isAuthenticated: true,
      hasAtLeastRole: vi.fn().mockReturnValue(false),
    });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/admin/tools",
      fullPath: "/admin/tools",
      meta: { minRole: "admin" },
      query: {},
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toEqual({
      name: "forbidden",
      query: { required: "admin", from: "/admin/tools" },
    });
  });

  it("preserves Klassrumskartan dashboard origin through the auth-login redirect", async () => {
    const auth = createAuth();
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      name: "app-detail",
      path: "/apps/classroom.group-seating-studio",
      fullPath: "/apps/classroom.group-seating-studio",
      params: { appId: "classroom.group-seating-studio" },
      meta: { requiresAuth: true },
      query: {},
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toEqual({
      name: "auth-login",
      query: {
        next: "/apps/classroom.group-seating-studio",
        classroomPlannerEntryOrigin: "dashboard",
      },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("redirects authenticated users away from auth-login using the preserved next param", async () => {
    const auth = createAuth({
      isAuthenticated: true,
      hasAtLeastRole: vi.fn().mockReturnValue(true),
    });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/auth/login",
      fullPath: "/auth/login?next=/profile",
      meta: {},
      query: { next: "/profile" },
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toEqual({ path: "/profile" });
  });

  it("restores classroom planner origin when auth-login is revisited authenticated", async () => {
    const auth = createAuth({
      isAuthenticated: true,
      hasAtLeastRole: vi.fn().mockReturnValue(true),
    });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/auth/login",
      fullPath: "/auth/login?next=/apps/classroom.group-seating-studio&classroomPlannerEntryOrigin=dashboard",
      meta: {},
      query: {
        next: "/apps/classroom.group-seating-studio",
        classroomPlannerEntryOrigin: "dashboard",
      },
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toEqual({
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
  });

  it("leaves the dedicated public curated app route unauthenticated", async () => {
    const auth = createAuth();
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      name: "public-app-detail",
      path: "/public/apps/classroom.group-seating-studio",
      fullPath: "/public/apps/classroom.group-seating-studio",
      params: { appId: "classroom.group-seating-studio" },
      meta: {},
      query: {},
    }, {
      name: "home",
    });

    expect(auth.bootstrap).not.toHaveBeenCalled();
    expect(result).toBe(true);
  });
});
