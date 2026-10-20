/**
 * Guest handoff superseded-success signal (TASK-SKRIPT-41-02-05, U8a).
 *
 * Expected behavior (rereview ba74ef97 R5, ledger D21):
 *   `protectedRequest` gains the per-request option `onSupersededSuccess`,
 *   called once when the server answered 2xx but this request's session
 *   retired before the response was admitted. The
 *   `SupersededAuthSessionError` still throws and the body is never read.
 *   An unanswered or failed request clears nothing. Ownership checks stay on
 *   for every other request, and the option never reaches `fetch`.
 */

import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SupersededAuthSessionError, useAuthStore } from "../stores/auth";
import { createTestUser, mockJsonResponse } from "../stores/authTestHelpers";
import { apiFetch } from "./client";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return { promise, reject, resolve };
}

function admitTeacher(id: string, csrfToken: string | null = `${id}-csrf`): void {
  const auth = useAuthStore();
  auth.clear();
  auth.$patch({
    user: createTestUser({ id, email: `${id}@example.test` }),
    sharedSessionId: `${id}-session`,
    csrfToken,
  });
}

function csrfRejection(): Response {
  return mockJsonResponse(
    {
      error: {
        code: "AUTHORIZATION_ERROR",
        message: "CSRF token required for browser session write",
      },
    },
    403,
  );
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.mocked(fetch).mockReset();
  admitTeacher("teacher-a");
});

describe("protectedRequest onSupersededSuccess", () => {
  it("is called exactly once for a 2xx answered after retirement, and the call still rejects", async () => {
    const auth = useAuthStore();
    const session = auth.captureSession();
    const onSupersededSuccess = vi.fn();
    const pendingBody = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(pendingBody.promise);
    const result = apiFetch("/api/v1/write", {
      body: { title: "A" },
      method: "POST",
      onSupersededSuccess,
      session,
    });
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    admitTeacher("teacher-b");
    pendingBody.resolve(mockJsonResponse({ result: "saved-by-a" }));
    await expect(result).rejects.toBeInstanceOf(SupersededAuthSessionError);
    expect(onSupersededSuccess).toHaveBeenCalledTimes(1);
  });

  it("is never called for a non-2xx answered after retirement", async () => {
    const auth = useAuthStore();
    const session = auth.captureSession();
    const onSupersededSuccess = vi.fn();
    const pendingBody = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(pendingBody.promise);
    const result = apiFetch("/api/v1/write", {
      body: { title: "A" },
      method: "POST",
      onSupersededSuccess,
      session,
    });
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    admitTeacher("teacher-b");
    pendingBody.resolve(
      mockJsonResponse({ error: { code: "VALIDATION_ERROR", message: "rejected" } }, 422),
    );
    await expect(result).rejects.toBeInstanceOf(SupersededAuthSessionError);
    expect(onSupersededSuccess).not.toHaveBeenCalled();
  });

  it("is never called for an unanswered request after retirement", async () => {
    const auth = useAuthStore();
    const session = auth.captureSession();
    const onSupersededSuccess = vi.fn();
    const pendingBody = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(pendingBody.promise);
    const result = apiFetch("/api/v1/write", {
      body: { title: "A" },
      method: "POST",
      onSupersededSuccess,
      session,
    });
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    admitTeacher("teacher-b");
    pendingBody.reject(new TypeError("network down"));
    await expect(result).rejects.toBeInstanceOf(SupersededAuthSessionError);
    expect(onSupersededSuccess).not.toHaveBeenCalled();
  });

  it("is never called when the session is current", async () => {
    const auth = useAuthStore();
    const session = auth.captureSession();
    const onSupersededSuccess = vi.fn();
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ result: "ok" }));
    await expect(
      apiFetch("/api/v1/write", {
        body: { title: "A" },
        method: "POST",
        onSupersededSuccess,
        session,
      }),
    ).resolves.toEqual({ result: "ok" });
    expect(auth.isCurrentSession(session)).toBe(true);
    expect(onSupersededSuccess).not.toHaveBeenCalled();
  });

  it("is never called when a CSRF 403 is followed by retirement during token recovery", async () => {
    const auth = useAuthStore();
    const session = auth.captureSession();
    const onSupersededSuccess = vi.fn();
    const pendingRejection = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(pendingRejection.promise);
    const result = apiFetch("/api/v1/write", {
      body: { title: "A" },
      method: "POST",
      onSupersededSuccess,
      session,
    });
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    admitTeacher("teacher-b");
    pendingRejection.resolve(csrfRejection());
    await expect(result).rejects.toBeInstanceOf(SupersededAuthSessionError);
    expect(onSupersededSuccess).not.toHaveBeenCalled();
  });

  it("is not passed to fetch", async () => {
    const auth = useAuthStore();
    const session = auth.captureSession();
    const onSupersededSuccess = vi.fn();
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ result: "ok" }));
    await apiFetch("/api/v1/write", {
      body: { title: "A" },
      method: "POST",
      onSupersededSuccess,
      session,
    });
    expect(fetch).toHaveBeenCalledTimes(1);
    const options = vi.mocked(fetch).mock.calls[0][1] ?? {};
    expect(options).not.toHaveProperty("onSupersededSuccess");
    expect(options).not.toHaveProperty("session");
  });
});
