import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiGet } from "../../api/client";
import { getAdminUser, getAdminUserLoginEvents, listAdminUsers } from "./useAdminUsers";

vi.mock("../../api/client", () => ({
  apiGet: vi.fn(),
}));

describe("useAdminUsers", () => {
  beforeEach(() => {
    vi.mocked(apiGet).mockReset();
  });

  describe("listAdminUsers()", () => {
    it("defaults to limit=50 offset=0", async () => {
      vi.mocked(apiGet).mockResolvedValueOnce({} as never);

      await listAdminUsers();

      expect(apiGet).toHaveBeenCalledWith("/api/v1/admin/users?limit=50&offset=0");
    });

    it("uses provided limit and offset", async () => {
      vi.mocked(apiGet).mockResolvedValueOnce({} as never);

      await listAdminUsers({ limit: 10, offset: 25 });

      expect(apiGet).toHaveBeenCalledWith("/api/v1/admin/users?limit=10&offset=25");
    });
  });

  describe("getAdminUser()", () => {
    it("calls the user endpoint", async () => {
      vi.mocked(apiGet).mockResolvedValueOnce({} as never);

      await getAdminUser("user-123");

      expect(apiGet).toHaveBeenCalledWith("/api/v1/admin/users/user-123");
    });
  });

  describe("getAdminUserLoginEvents()", () => {
    it("defaults to limit=50", async () => {
      vi.mocked(apiGet).mockResolvedValueOnce({} as never);

      await getAdminUserLoginEvents("user-123");

      expect(apiGet).toHaveBeenCalledWith("/api/v1/admin/users/user-123/login-events?limit=50");
    });

    it("uses provided limit", async () => {
      vi.mocked(apiGet).mockResolvedValueOnce({} as never);

      await getAdminUserLoginEvents("user-123", { limit: 15 });

      expect(apiGet).toHaveBeenCalledWith("/api/v1/admin/users/user-123/login-events?limit=15");
    });
  });
});
