import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

const mockUseAuthStore = vi.fn();
const mockUseLoginModal = vi.fn();
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

vi.mock("../composables/useLoginModal", () => ({
  useLoginModal: mockUseLoginModal,
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

function createLoginModal() {
  return { open: vi.fn() };
}

beforeAll(async () => {
  await import("./index");
});

beforeEach(async () => {
  mockUseAuthStore.mockReset();
  mockUseLoginModal.mockReset();
});

describe("router guards", () => {
  it("opens login modal and aborts when auth is required and user is unauthenticated", async () => {
    const auth = createAuth();
    const loginModal = createLoginModal();
    mockUseAuthStore.mockReturnValue(auth);
    mockUseLoginModal.mockReturnValue(loginModal);

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
    expect(loginModal.open).toHaveBeenCalledWith("/browse");
    expect(result).toBe(false);
  });

  it("redirects authenticated users away from /login to the next param", async () => {
    const auth = createAuth({
      isAuthenticated: true,
      hasAtLeastRole: vi.fn().mockReturnValue(true),
    });
    const loginModal = createLoginModal();
    mockUseAuthStore.mockReturnValue(auth);
    mockUseLoginModal.mockReturnValue(loginModal);

    const guard = registeredGuard;
    if (!guard) throw new Error("Router guard not registered");
    const result = await guard({
      path: "/login",
      fullPath: "/login?next=/profile",
      meta: {},
      query: { next: "/profile" },
    }, {
      name: undefined,
    });

    expect(auth.bootstrap).toHaveBeenCalled();
    expect(loginModal.open).not.toHaveBeenCalled();
    expect(result).toEqual({ path: "/profile" });
  });

  it("redirects to forbidden when minRole is not satisfied", async () => {
    const auth = createAuth({
      isAuthenticated: true,
      hasAtLeastRole: vi.fn().mockReturnValue(false),
    });
    const loginModal = createLoginModal();
    mockUseAuthStore.mockReturnValue(auth);
    mockUseLoginModal.mockReturnValue(loginModal);

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
    expect(loginModal.open).not.toHaveBeenCalled();
    expect(result).toEqual({
      name: "forbidden",
      query: { required: "admin", from: "/admin/tools" },
    });
  });

  it("preserves Klassrumskartan dashboard origin through the login modal redirect", async () => {
    const auth = createAuth();
    const loginModal = createLoginModal();
    mockUseAuthStore.mockReturnValue(auth);
    mockUseLoginModal.mockReturnValue(loginModal);

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
    expect(loginModal.open).toHaveBeenCalledWith({
      name: "app-detail",
      params: { appId: "classroom.group-seating-studio" },
      state: {
        classroomPlannerEntryOrigin: "dashboard",
      },
    });
    expect(result).toBe(false);
  });

  it("leaves the dedicated public curated app route unauthenticated", async () => {
    const auth = createAuth();
    const loginModal = createLoginModal();
    mockUseAuthStore.mockReturnValue(auth);
    mockUseLoginModal.mockReturnValue(loginModal);

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
    expect(loginModal.open).not.toHaveBeenCalled();
    expect(result).toBe(true);
  });
});
