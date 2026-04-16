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
  isProvisioningRequired?: boolean;
  hasAtLeastRole?: (role: string) => boolean;
}) {
  return {
    isAuthenticated: overrides?.isAuthenticated ?? false,
    isProvisioningRequired: overrides?.isProvisioningRequired ?? false,
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

  it("redirects authenticated HuleEdu users without a local projection to provisioning-required", async () => {
    const auth = createAuth({ isProvisioningRequired: true });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/editor",
      fullPath: "/editor",
      meta: { requiresAuth: true, minRole: "contributor" },
      query: {},
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toEqual({
      name: "auth-provisioning-required",
      query: { from: "/editor" },
    });
  });

  it("keeps missing-projection users on the provisioning-required route", async () => {
    const auth = createAuth({ isProvisioningRequired: true });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      name: "auth-provisioning-required",
      path: "/auth/provisioning-required",
      fullPath: "/auth/provisioning-required?from=/editor",
      meta: {},
      query: { from: "/editor" },
    }, {
      name: "editor-hub",
      fullPath: "/editor",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toBe(true);
  });

  it("sends anonymous provisioning-required visits through auth-login with the original route", async () => {
    const auth = createAuth();
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      name: "auth-provisioning-required",
      path: "/auth/provisioning-required",
      fullPath: "/auth/provisioning-required?from=/editor",
      meta: {},
      query: { from: "/editor" },
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toEqual({
      name: "auth-login",
      query: { next: "/editor" },
    });
  });

  it("resumes the original route when a ready user revisits provisioning-required", async () => {
    const auth = createAuth({
      isAuthenticated: true,
      hasAtLeastRole: vi.fn().mockReturnValue(true),
    });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      name: "auth-provisioning-required",
      path: "/auth/provisioning-required",
      fullPath: "/auth/provisioning-required?from=/editor",
      meta: {},
      query: { from: "/editor" },
    }, {
      name: "auth-login",
      fullPath: "/auth/login?next=/auth/provisioning-required?from=/editor",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toBe("/editor");
  });

  it("falls home when a ready user revisits provisioning-required without a safe from route", async () => {
    const auth = createAuth({
      isAuthenticated: true,
      hasAtLeastRole: vi.fn().mockReturnValue(true),
    });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      name: "auth-provisioning-required",
      path: "/auth/provisioning-required",
      fullPath: "/auth/provisioning-required?from=https://example.com/phish",
      meta: {},
      query: { from: "https://example.com/phish" },
    }, {
      name: "auth-login",
      fullPath: "/auth/login?next=/auth/provisioning-required",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toBe("/");
  });

  it("preserves full protected route destinations through auth-login", async () => {
    const auth = createAuth();
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/admin/tools",
      fullPath: "/admin/tools?status=draft#review",
      meta: { requiresAuth: true, minRole: "admin" },
      query: { status: "draft" },
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toEqual({
      name: "auth-login",
      query: { next: "/admin/tools?status=draft#review" },
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
    expect(result).toBe("/profile");
  });

  it("resumes the next route when auth-login bootstrap finds a HuleEdu session", async () => {
    const auth = createAuth();
    auth.bootstrap.mockImplementation(async () => {
      auth.isAuthenticated = true;
    });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/auth/login",
      fullPath: "/auth/login?next=/editor",
      meta: {},
      query: { next: "/editor" },
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toBe("/editor");
  });

  it("resumes the next route when auth-callback bootstrap finds a HuleEdu session", async () => {
    const auth = createAuth();
    auth.bootstrap.mockImplementation(async () => {
      auth.isAuthenticated = true;
    });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/auth/callback",
      fullPath: "/auth/callback?next=/editor",
      meta: {},
      query: { next: "/editor" },
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toBe("/editor");
  });

  it("preserves callback query and hash destinations as a route string", async () => {
    const auth = createAuth();
    auth.bootstrap.mockImplementation(async () => {
      auth.isAuthenticated = true;
    });
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/auth/callback",
      fullPath: "/auth/callback?next=/admin/tools?status=draft%23review",
      meta: {},
      query: { next: "/admin/tools?status=draft#review" },
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toBe("/admin/tools?status=draft#review");
  });

  it("keeps anonymous HuleEdu sessions on auth-login with next intact", async () => {
    const auth = createAuth();
    mockUseAuthStore.mockReturnValue(auth);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/auth/login",
      fullPath: "/auth/login?next=/editor",
      meta: {},
      query: { next: "/editor" },
    }, {
      name: "home",
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(result).toBe(true);
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
