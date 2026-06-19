/**
 * Authenticated home dashboard loader tests.
 *
 * Domain purpose:
 * - proves the app-first home route loads only data required by visible ledgers
 * - guards retired runs/favorites/recent endpoints from re-entering the default
 *   authenticated `/` loading path
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiGet } from "../../api/client";
import { useHomeDashboard } from "./useHomeDashboard";

const favoritesMocks = vi.hoisted(() => ({
  toggleFavorite: vi.fn(),
  isToggling: vi.fn(() => false),
}));

vi.mock("../../api/client", () => ({
  apiGet: vi.fn(),
  isApiError: vi.fn(() => false),
}));

vi.mock("../useFavorites", () => ({
  useFavorites: () => favoritesMocks,
}));

function mockApiGetByPath() {
  vi.mocked(apiGet).mockImplementation(async (path: string) => {
    if (path === "/api/v1/my-tools") {
      return {
        tools: [
          { is_published: true },
          { is_published: false },
        ],
      } as never;
    }

    if (path === "/api/v1/admin/tools") {
      return {
        tools: [
          { is_published: true, has_pending_review: true },
          { is_published: false, has_pending_review: false },
        ],
      } as never;
    }

    if (path === "/api/v1/my-runs") {
      return {
        total_count: 2,
        runs: [{ id: "run-1" }, { id: "run-2" }],
      } as never;
    }

    if (path === "/api/v1/favorites?limit=5") {
      return {
        items: [],
      } as never;
    }

    if (path === "/api/v1/me/recent-tools?limit=5") {
      return {
        items: [],
      } as never;
    }

    throw new Error(`Unexpected apiGet path: ${path}`);
  });
}

describe("useHomeDashboard loader boundary", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockReset();
    favoritesMocks.toggleFavorite.mockReset();
    favoritesMocks.isToggling.mockReset();
    favoritesMocks.isToggling.mockReturnValue(false);
    mockApiGetByPath();
  });

  it("does not call retired runs favorites or recent-tool endpoints for the teacher home surface", async () => {
    const dashboard = useHomeDashboard();

    await dashboard.loadDashboard({
      isContributor: false,
      isAdmin: false,
    });

    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/my-runs");
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/favorites?limit=5");
    expect(apiGet).not.toHaveBeenCalledWith("/api/v1/me/recent-tools?limit=5");
    expect(apiGet).not.toHaveBeenCalled();
  });

  it("loads only contributor and admin ledger data when those ledgers are visible", async () => {
    const dashboard = useHomeDashboard();

    await dashboard.loadDashboard({
      isContributor: true,
      isAdmin: true,
    });

    expect(apiGet).toHaveBeenCalledWith("/api/v1/my-tools");
    expect(apiGet).toHaveBeenCalledWith("/api/v1/admin/tools");
    expect(vi.mocked(apiGet).mock.calls.map(([path]) => path)).toEqual([
      "/api/v1/my-tools",
      "/api/v1/admin/tools",
    ]);
    expect(dashboard.toolsTotal.value).toBe(2);
    expect(dashboard.toolsPublished.value).toBe(1);
    expect(dashboard.adminPendingReview.value).toBe(1);
  });
});
