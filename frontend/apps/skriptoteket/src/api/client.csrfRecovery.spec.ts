import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SupersededAuthSessionError, useAuthStore } from "../stores/auth";
import { createTestProfile, createTestUser, mockJsonResponse, mockSharedSessionResponse as serverSession } from "../stores/authTestHelpers";
import { postChatStream } from "../composables/editor/chat/editorChatApi";
import { cancelTranscriptJob, submitTranscriptJob } from "./sirConvertGateway/client";
import { apiFetch, apiFetchBlob, apiFetchBlobResponse, apiPost, isApiError } from "./client";

const rejection = () => mockJsonResponse({ error: {
  code: "AUTHORIZATION_ERROR", message: "CSRF token required for browser session write",
  details: { session_cookie_present: true, csrf_cookie_present: true, csrf_header_present: true },
} }, 403);
const job = { job: { job_id: "job-a", status: "queued" } };
function file() {
  const result = new File(["audio"], "lesson.wav");
  Object.defineProperty(result, "arrayBuffer", { value: async () => new ArrayBuffer(5) });
  return result;
}
const transports = [
  { name: "JSON", request: () => apiFetch("/api/v1/write", { method: "PUT", body: { title: "A" } }) },
  { name: "blob", request: () => apiFetchBlob("/api/v1/write", { method: "POST", body: new Blob(["A"]) }) },
  { name: "blob metadata", request: () => apiFetchBlobResponse("/api/v1/write", { method: "POST", body: new FormData() }) },
  { name: "chat", request: async () => {
    const response = await postChatStream({ toolId: "a", body: { message: "A" }, correlationId: "corr-a", signal: new AbortController().signal });
    if (!response.ok) throw new Error("Rejected");
    return response;
  } },
  { name: "Gateway cancellation", request: () => cancelTranscriptJob({ jobId: "job-a", correlationId: "corr-a" }) },
  { name: "Gateway upload", request: () => submitTranscriptJob({ file: file(), correlationId: "corr-a", speakerControl: { mode: "auto" } }) },
  { name: "logout", request: () => useAuthStore().logout() },
];
beforeEach(async () => {
  setActivePinia(createPinia());
  vi.mocked(fetch).mockReset();
  vi.mocked(fetch).mockResolvedValueOnce(serverSession())
    .mockResolvedValueOnce(mockJsonResponse({
      local_user: createTestUser(), profile: createTestProfile(),
    }))
    .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "stale" }))
    .mockResolvedValueOnce(serverSession());
  await useAuthStore().bootstrap();
  vi.mocked(fetch).mockReset();
});

it("rejects a one-shot request stream before dispatch instead of replaying consumed data", async () => {
  await expect(apiFetch("/api/v1/write", {
    method: "POST", body: new ReadableStream(),
  })).rejects.toThrow("Stream request bodies are not replayable");
  expect(fetch).not.toHaveBeenCalled();
});

it("surfaces the original CSRF failure when the session authority cannot answer", async () => {
  vi.mocked(fetch).mockResolvedValueOnce(rejection())
    .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "unverified" }))
    .mockRejectedValueOnce(new Error("Session lookup offline"));
  await expect(apiFetch("/api/v1/write", { method: "PUT", body: { title: "A" } }))
    .rejects.toMatchObject({
      status: 403, code: "AUTHORIZATION_ERROR", message: "CSRF token required for browser session write",
    });
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(useAuthStore().csrfToken).toBeNull();
});

describe.each(transports)("$name CSRF recovery", ({ name: transportName, request }) => {
  it("replays the same payload once with a rehydrated token", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(rejection())
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh" }))
      .mockResolvedValueOnce(serverSession())
      .mockResolvedValueOnce(mockJsonResponse(job));
    await request();
    const calls = vi.mocked(fetch).mock.calls;
    expect(calls).toHaveLength(4);
    expect(String(calls[1][0])).toContain("/auth/csrf");
    expect(new Headers(calls[0][1]?.headers).get("X-CSRF-Token")).toBe("stale");
    expect(String(calls[2][0])).toContain("/auth/session");
    expect(calls[1][1]?.cache).toBe("no-store");
    expect(calls[2][1]?.cache).toBe("no-store");
    expect(new Headers(calls[3][1]?.headers).get("X-CSRF-Token")).toBe("fresh");
    expect(calls[3][0]).toBe(calls[0][0]);
    expect(calls[3][1]?.body).toEqual(calls[0][1]?.body);
  });
  it("surfaces a second CSRF rejection without a loop", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(rejection())
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh" }))
      .mockResolvedValueOnce(serverSession())
      .mockResolvedValueOnce(rejection());
    await expect(request()).rejects.toThrow();
    expect(fetch).toHaveBeenCalledTimes(4);
  });
  it("does not replay a non-CSRF authorization denial", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ error: {
      code: "AUTHORIZATION_ERROR", message: "Not permitted",
    } }, 403));
    await expect(request()).rejects.toThrow();
    expect(fetch).toHaveBeenCalledOnce();
    expect(useAuthStore().csrfToken).toBe("stale");
  });
  it("does not replay when token rehydration fails", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(rejection())
      .mockResolvedValueOnce(mockJsonResponse({ error: { message: "Unavailable" } }, 503));
    await expect(request()).rejects.toThrow();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it.each([
    ["another account", () => serverSession("session-b", "provider-b")],
    ["a new session for the same account", () => serverSession("session-b")],
    ["an unidentified session", () => serverSession(null)],
    ["an expired session", () => mockJsonResponse({}, 401)],
    ["an unavailable session authority", () => mockJsonResponse({}, 503)],
  ])("refuses replay under %s without adopting its identity", async (name, replacement) => {
    const auth = useAuthStore();
    const originalUser = auth.user;
    const originalSession = auth.captureSession();
    vi.mocked(fetch).mockResolvedValueOnce(rejection())
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "replacement-token" }))
      .mockResolvedValueOnce(replacement())
      .mockResolvedValueOnce(mockJsonResponse(job));
    if (transportName === "logout" && name !== "an unavailable session authority") {
      await expect(request()).resolves.toBeUndefined();
    } else {
      await expect(request()).rejects.toThrow();
    }
    expect(vi.mocked(fetch).mock.calls.filter(([, init]) => init?.method !== "GET")).toHaveLength(1);
    if (name === "an unavailable session authority") {
      expect(auth.user).toBe(originalUser);
      expect(auth.isCurrentSession(originalSession)).toBe(true);
    } else {
      expect(auth.user).toBeNull();
      expect(auth.isCurrentSession(originalSession)).toBe(false);
    }
    expect(auth.csrfToken).toBeNull();
  });
  it("refuses recovery when the originating session could not be identified at admission", async () => {
    const auth = useAuthStore();
    auth.clear();
    auth.bootstrapped = false;
    vi.mocked(fetch).mockResolvedValueOnce(serverSession(null))
      .mockResolvedValueOnce(mockJsonResponse({
        local_user: createTestUser(), profile: createTestProfile(),
      }))
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "stale" }));
    await auth.bootstrap();
    vi.mocked(fetch).mockReset().mockResolvedValueOnce(rejection())
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "unbound" }))
      .mockResolvedValueOnce(mockJsonResponse(job));
    await expect(request()).rejects.toThrow();
    // A write without a token is never dispatched, so no transport reaches fetch.
    expect(fetch).toHaveBeenCalledTimes(0);
    expect(auth.csrfToken).toBeNull();
  });
  it("never replays across a session change during rehydration", async () => {
    const auth = useAuthStore();
    vi.mocked(fetch).mockResolvedValueOnce(rejection()).mockImplementationOnce(async () => {
      auth.clear();
      auth.user = createTestUser({ id: "teacher-b" });
      auth.csrfToken = "B";
      return mockJsonResponse({ csrf_token: "A-late" });
    });
    const result = await request().catch((error: unknown) => error);
    if (result !== undefined) expect(result).toBeInstanceOf(SupersededAuthSessionError);
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(auth.csrfToken).toBe("B");
  });
});

describe("missing CSRF token", () => {
  const claimPath = "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/lineage-1/edit-lease/claim";

  function claimWasSent(): boolean {
    return vi.mocked(fetch).mock.calls
      .map(([url]) => String(url))
      .some((url) => url.includes("/edit-lease/claim"));
  }

  it("rejects an edit-lease claim without sending it when the token load returns an error", async () => {
    useAuthStore().csrfToken = null;
    vi.mocked(fetch)
      .mockResolvedValueOnce(mockJsonResponse({ error: { message: "Unavailable" } }, 503))
      .mockResolvedValueOnce(mockJsonResponse({ lease: "claimed" }));
    const result = await apiPost(claimPath, { owner: "teacher-a" }).then(
      () => null,
      (error: unknown) => error,
    );
    expect(isApiError(result)).toBe(true);
    expect(result).toMatchObject({
      status: 403,
      code: "AUTHORIZATION_ERROR",
      message: "CSRF token required for browser session write",
    });
    expect(claimWasSent()).toBe(false);
  });

  it("rejects an edit-lease claim without sending it when the token load throws", async () => {
    useAuthStore().csrfToken = null;
    vi.mocked(fetch)
      .mockRejectedValueOnce(new Error("Det gick inte att hämta CSRF-token."))
      .mockResolvedValueOnce(mockJsonResponse({ lease: "claimed" }));
    const result = await apiPost(claimPath, { owner: "teacher-a" }).then(
      () => null,
      (error: unknown) => error,
    );
    expect(isApiError(result)).toBe(true);
    expect(result).toMatchObject({
      status: 403,
      code: "AUTHORIZATION_ERROR",
      message: "CSRF token required for browser session write",
    });
    expect(claimWasSent()).toBe(false);
  });

  it("sends the claim once with its header when the token is available", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ lease: "claimed" }));
    await apiPost(claimPath, { owner: "teacher-a" });
    expect(fetch).toHaveBeenCalledOnce();
    expect(new Headers(vi.mocked(fetch).mock.calls[0][1]?.headers).get("X-CSRF-Token")).toBe("stale");
  });
});
