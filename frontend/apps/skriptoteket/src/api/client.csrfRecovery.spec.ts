import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SupersededAuthSessionError, useAuthStore } from "../stores/auth";
import { createTestUser, mockJsonResponse } from "../stores/authTestHelpers";
import { postChatStream } from "../composables/editor/chat/editorChatApi";
import { cancelTranscriptJob, submitTranscriptJob } from "./sirConvertGateway/client";
import { apiFetch, apiFetchBlob, apiFetchBlobResponse } from "./client";

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
beforeEach(() => {
  setActivePinia(createPinia());
  vi.mocked(fetch).mockReset();
  const auth = useAuthStore();
  auth.user = createTestUser();
  auth.csrfToken = "stale";
  auth.bootstrapped = true;
});

it("rejects a one-shot request stream before dispatch instead of replaying consumed data", async () => {
  await expect(apiFetch("/api/v1/write", {
    method: "POST", body: new ReadableStream(),
  })).rejects.toThrow("Stream request bodies are not replayable");
  expect(fetch).not.toHaveBeenCalled();
});

describe.each(transports)("$name CSRF recovery", ({ request }) => {
  it("replays the same payload once with a rehydrated token", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(rejection())
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh" }))
      .mockResolvedValueOnce(mockJsonResponse(job));
    await request();
    const calls = vi.mocked(fetch).mock.calls;
    expect(calls).toHaveLength(3);
    expect(String(calls[1][0])).toContain("/auth/csrf");
    expect(new Headers(calls[0][1]?.headers).get("X-CSRF-Token")).toBe("stale");
    expect(new Headers(calls[2][1]?.headers).get("X-CSRF-Token")).toBe("fresh");
    expect(calls[2][0]).toBe(calls[0][0]);
    expect(calls[2][1]?.body).toEqual(calls[0][1]?.body);
  });
  it("surfaces a second CSRF rejection without a loop", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(rejection())
      .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh" }))
      .mockResolvedValueOnce(rejection());
    await expect(request()).rejects.toThrow();
    expect(fetch).toHaveBeenCalledTimes(3);
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
