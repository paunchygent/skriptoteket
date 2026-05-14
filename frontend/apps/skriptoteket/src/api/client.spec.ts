import { afterEach, describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import {
  ApiError,
  DEFAULT_PROTECTED_API_BASE_URL,
  apiFetch,
  apiFetchBlob,
  apiGet,
  apiPost,
  isApiError,
  publicApiGet,
  resolveProtectedApiUrl,
} from "./client";
import { useAuthStore } from "../stores/auth";
import type { components } from "./openapi";

type ApiUser = components["schemas"]["User"];

// Test factory - creates minimal user for testing
function createTestUser(overrides: Partial<ApiUser> = {}): ApiUser {
  return {
    id: "550e8400-e29b-41d4-a716-446655440000",
    email: "test@test.com",
    role: "user",
    auth_provider: "local",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    email_verified: true,
    failed_login_attempts: 0,
    is_active: true,
    ...overrides,
  };
}

describe("client", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(fetch).mockReset();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  describe("resolveProtectedApiUrl()", () => {
    it("keeps protected app API paths relative in local development", () => {
      expect(resolveProtectedApiUrl("/api/v1/profile/app-continuation")).toBe(
        "/api/v1/profile/app-continuation",
      );
    });

    it("resolves protected app API paths through the configured edge", () => {
      vi.stubEnv("VITE_HULEEDU_PROTECTED_API_BASE_URL", `${DEFAULT_PROTECTED_API_BASE_URL}/`);

      expect(resolveProtectedApiUrl("/api/v1/profile/app-continuation")).toBe(
        `${DEFAULT_PROTECTED_API_BASE_URL}/v1/profile/app-continuation`,
      );
    });

    it("keeps public app API paths app-hosted even when a protected edge is configured", () => {
      vi.stubEnv("VITE_HULEEDU_PROTECTED_API_BASE_URL", DEFAULT_PROTECTED_API_BASE_URL);

      expect(resolveProtectedApiUrl("/api/v1/public/apps/example")).toBe(
        "/api/v1/public/apps/example",
      );
    });

    it("leaves non-app API URLs unchanged", () => {
      vi.stubEnv("VITE_HULEEDU_PROTECTED_API_BASE_URL", DEFAULT_PROTECTED_API_BASE_URL);

      expect(resolveProtectedApiUrl("https://files.example.test/download")).toBe(
        "https://files.example.test/download",
      );
    });
  });

  describe("ApiError", () => {
    it("creates error with all properties", () => {
      const error = new ApiError({
        code: "NOT_FOUND",
        message: "Resource not found",
        status: 404,
        details: { id: 123 },
        correlationId: "abc-123",
      });

      expect(error.name).toBe("ApiError");
      expect(error.code).toBe("NOT_FOUND");
      expect(error.message).toBe("Resource not found");
      expect(error.status).toBe(404);
      expect(error.details).toEqual({ id: 123 });
      expect(error.correlationId).toBe("abc-123");
    });

    it("defaults optional properties to null", () => {
      const error = new ApiError({
        code: "ERROR",
        message: "Something went wrong",
        status: 500,
      });

      expect(error.details).toBeNull();
      expect(error.correlationId).toBeNull();
    });

    it("is instanceof Error", () => {
      const error = new ApiError({
        code: "ERROR",
        message: "Test",
        status: 500,
      });

      expect(error instanceof Error).toBe(true);
      expect(error instanceof ApiError).toBe(true);
    });
  });

  describe("isApiError()", () => {
    it("returns true for ApiError instances", () => {
      const error = new ApiError({
        code: "ERROR",
        message: "Test",
        status: 500,
      });

      expect(isApiError(error)).toBe(true);
    });

    it("returns false for regular Error", () => {
      expect(isApiError(new Error("test"))).toBe(false);
    });

    it("returns false for non-error objects", () => {
      expect(isApiError({ code: "ERROR", message: "test" })).toBe(false);
      expect(isApiError(null)).toBe(false);
      expect(isApiError(undefined)).toBe(false);
      expect(isApiError("error")).toBe(false);
    });
  });

  describe("apiFetch()", () => {
    function mockResponse(data: unknown, status = 200, contentType = "application/json") {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: status >= 200 && status < 300,
        status,
        statusText: status === 200 ? "OK" : "Error",
        headers: new Headers({ "content-type": contentType }),
        json: () => Promise.resolve(data),
        text: () => Promise.resolve(typeof data === "string" ? data : JSON.stringify(data)),
      } as Response);
    }

    it("makes GET request with correct headers", async () => {
      mockResponse({ result: "ok" });

      await apiFetch("/api/test");

      expect(fetch).toHaveBeenCalledWith("/api/test", {
        method: "GET",
        headers: expect.any(Headers),
        body: undefined,
        credentials: "include",
      });

      const headers = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers as Headers;
      expect(headers.get("Accept")).toBe("application/json");
    });

    it("uses the configured protected API edge for app API requests", async () => {
      vi.stubEnv("VITE_HULEEDU_PROTECTED_API_BASE_URL", DEFAULT_PROTECTED_API_BASE_URL);
      mockResponse({ result: "ok" });

      await apiFetch("/api/test");

      expect(fetch).toHaveBeenCalledWith(
        `${DEFAULT_PROTECTED_API_BASE_URL}/test`,
        expect.objectContaining({ method: "GET", credentials: "include" }),
      );
    });

    it("returns parsed JSON on success", async () => {
      mockResponse({ data: "test" });

      const result = await apiFetch("/api/test");

      expect(result).toEqual({ data: "test" });
    });

    it("returns undefined for 204 No Content", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        status: 204,
        headers: new Headers(),
      } as Response);

      const result = await apiFetch("/api/test");

      expect(result).toBeUndefined();
    });

    it("returns text for non-JSON content type", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "text/plain" }),
        text: () => Promise.resolve("plain text response"),
      } as Response);

      const result = await apiFetch("/api/test");

      expect(result).toBe("plain text response");
    });

    it("adds CSRF token for non-GET requests", async () => {
      const auth = useAuthStore();
      auth.csrfToken = "test-csrf-token";
      mockResponse({ result: "ok" });

      await apiFetch("/api/test", { method: "POST" });

      const headers = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers as Headers;
      expect(headers.get("X-CSRF-Token")).toBe("test-csrf-token");
    });

    it("fetches CSRF from the shared HuleEdu edge before unsafe requests", async () => {
      const auth = useAuthStore();
      auth.user = createTestUser();
      vi.mocked(fetch)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: () => Promise.resolve({ csrf_token: "shared-csrf-token" }),
        } as Response)
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: () => Promise.resolve({ result: "ok" }),
        } as Response);

      await apiFetch("/api/test", { method: "PATCH", body: { foo: "bar" } });

      expect(fetch).toHaveBeenNthCalledWith(
        1,
        "https://api.hule.education/v1/auth/csrf",
        expect.objectContaining({ method: "GET", credentials: "include" }),
      );
      const headers = (fetch as ReturnType<typeof vi.fn>).mock.calls[1][1].headers as Headers;
      expect(headers.get("X-CSRF-Token")).toBe("shared-csrf-token");
      expect(headers.get("Authorization")).toBeNull();
    });

    it("does not add CSRF token for GET requests", async () => {
      const auth = useAuthStore();
      auth.csrfToken = "test-csrf-token";
      mockResponse({ result: "ok" });

      await apiFetch("/api/test", { method: "GET" });

      const headers = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers as Headers;
      expect(headers.get("X-CSRF-Token")).toBeNull();
    });

    it("serializes JSON body", async () => {
      mockResponse({ result: "ok" });

      await apiFetch("/api/test", { method: "POST", body: { foo: "bar" } });

      const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(call[1].body).toBe('{"foo":"bar"}');

      const headers = call[1].headers as Headers;
      expect(headers.get("Content-Type")).toBe("application/json");
    });

    it("passes FormData directly without JSON serialization", async () => {
      mockResponse({ result: "ok" });
      const formData = new FormData();
      formData.append("file", "test");

      await apiFetch("/api/test", { method: "POST", body: formData });

      const call = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(call[1].body).toBe(formData);
    });

    it("clears auth on 401 response", async () => {
      const auth = useAuthStore();
      auth.user = createTestUser();

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve({ error: { code: "UNAUTHORIZED", message: "Not logged in" } }),
      } as Response);

      await expect(apiFetch("/api/test")).rejects.toThrow();
      expect(auth.user).toBeNull();
    });

    describe("error parsing", () => {
      it("parses structured API error envelope", async () => {
        vi.mocked(fetch).mockResolvedValueOnce({
          ok: false,
          status: 400,
          statusText: "Bad Request",
          headers: new Headers({ "content-type": "application/json" }),
          json: () =>
            Promise.resolve({
              error: { code: "INVALID_INPUT", message: "Invalid data" },
              correlation_id: "corr-123",
            }),
        } as Response);

        try {
          await apiFetch("/api/test");
          expect.fail("Should have thrown");
        } catch (error) {
          expect(isApiError(error)).toBe(true);
          if (isApiError(error)) {
            expect(error.code).toBe("INVALID_INPUT");
            expect(error.message).toBe("Invalid data");
            expect(error.correlationId).toBe("corr-123");
            expect(error.status).toBe(400);
          }
        }
      });

      it("parses FastAPI validation error", async () => {
        vi.mocked(fetch).mockResolvedValueOnce({
          ok: false,
          status: 422,
          statusText: "Unprocessable Entity",
          headers: new Headers({ "content-type": "application/json" }),
          json: () =>
            Promise.resolve({
              detail: [{ loc: ["body", "name"], msg: "field required", type: "value_error" }],
            }),
        } as Response);

        try {
          await apiFetch("/api/test");
          expect.fail("Should have thrown");
        } catch (error) {
          expect(isApiError(error)).toBe(true);
          if (isApiError(error)) {
            expect(error.code).toBe("VALIDATION_ERROR");
            expect(error.details).toEqual([
              { loc: ["body", "name"], msg: "field required", type: "value_error" },
            ]);
          }
        }
      });

      it("falls back to HTTP error for non-JSON response", async () => {
        vi.mocked(fetch).mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
          headers: new Headers({ "content-type": "text/html" }),
          text: () => Promise.resolve("<html>Error</html>"),
        } as Response);

        try {
          await apiFetch("/api/test");
          expect.fail("Should have thrown");
        } catch (error) {
          expect(isApiError(error)).toBe(true);
          if (isApiError(error)) {
            expect(error.code).toBe("HTTP_ERROR");
            expect(error.message).toBe("Internal Server Error");
          }
        }
      });
    });
  });

  describe("apiGet()", () => {
    it("calls apiFetch with GET method", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve({ data: "test" }),
      } as Response);

      const result = await apiGet("/api/test");

      expect(result).toEqual({ data: "test" });
      expect(fetch).toHaveBeenCalledWith("/api/test", expect.objectContaining({ method: "GET" }));
    });
  });

  describe("apiPost()", () => {
    it("calls apiFetch with POST method and body", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve({ data: "result" }),
      } as Response);

      const result = await apiPost("/api/test", { input: "value" });

      expect(result).toEqual({ data: "result" });
      expect(fetch).toHaveBeenCalledWith(
        "/api/test",
        expect.objectContaining({
          method: "POST",
          body: '{"input":"value"}',
        }),
      );
    });
  });

  describe("publicApiGet()", () => {
    it("omits credentials for public app bootstrap requests", async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve({ data: "public" }),
      } as Response);

      const result = await publicApiGet(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter",
      );

      expect(result).toEqual({ data: "public" });
      expect(fetch).toHaveBeenCalledWith(
        "/api/v1/public/apps/documents.conversion_hub/exam-converter",
        expect.objectContaining({ method: "GET", credentials: "omit" }),
      );
    });
  });

  describe("apiFetchBlob()", () => {
    it("uses the configured protected API edge for artifact downloads", async () => {
      vi.stubEnv("VITE_HULEEDU_PROTECTED_API_BASE_URL", DEFAULT_PROTECTED_API_BASE_URL);
      const blob = new Blob(["artifact"]);
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers(),
        blob: () => Promise.resolve(blob),
      } as Response);

      const result = await apiFetchBlob("/api/v1/runs/run-1/artifacts/artifact-1/download");

      expect(result).toBe(blob);
      expect(fetch).toHaveBeenCalledWith(
        `${DEFAULT_PROTECTED_API_BASE_URL}/v1/runs/run-1/artifacts/artifact-1/download`,
        expect.objectContaining({ method: "GET", credentials: "include" }),
      );
    });
  });
});
