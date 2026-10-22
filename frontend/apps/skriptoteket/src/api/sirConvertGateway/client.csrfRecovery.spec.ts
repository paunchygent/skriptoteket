import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SupersededAuthSessionError, useAuthStore } from "../../stores/auth";
import { createTestProfile, createTestUser, mockJsonResponse, mockSharedSessionResponse } from "../../stores/authTestHelpers";
import { submitTranscriptJob } from "./client";

const csrfError = { error: { code: "AUTHORIZATION_ERROR", message: "CSRF token required for browser session write" } };
class NetworkXhr {
  static responses: { status: number; body: unknown }[] = [];
  static sent: { body: unknown; headers: Headers }[] = [];
  upload = { onprogress: null };
  onload: (() => void) | null = null;
  onerror = null;
  onabort = null;
  status = 0;
  statusText = "";
  responseText = "";
  withCredentials = false;
  headers = new Headers();
  open() {}
  setRequestHeader(key: string, value: string) { this.headers.set(key, value); }
  getAllResponseHeaders() { return "content-type: application/json"; }
  send(body: unknown) {
    NetworkXhr.sent.push({ body, headers: new Headers(this.headers) });
    const response = NetworkXhr.responses.shift();
    if (!response) throw new Error("Unexpected replay");
    this.status = response.status;
    this.responseText = JSON.stringify(response.body);
    queueMicrotask(() => this.onload?.());
  }
  abort() {}
}
function submit() {
  const file = new File(["audio"], "lesson.wav");
  Object.defineProperty(file, "arrayBuffer", { value: async () => new ArrayBuffer(5) });
  return submitTranscriptJob({ file, correlationId: "corr-a", speakerControl: { mode: "auto" }, onUploadProgress: vi.fn() });
}
beforeEach(async () => {
  setActivePinia(createPinia());
  vi.mocked(fetch).mockReset();
  vi.mocked(fetch).mockResolvedValueOnce(mockSharedSessionResponse())
    .mockResolvedValueOnce(mockJsonResponse({
      local_user: createTestUser(), profile: createTestProfile(),
    }))
    .mockResolvedValueOnce(mockJsonResponse({ csrf_token: "stale" }))
    .mockResolvedValueOnce(mockSharedSessionResponse());
  await useAuthStore().bootstrap();
  vi.mocked(fetch).mockReset();
  NetworkXhr.sent = [];
  NetworkXhr.responses = [{ status: 403, body: csrfError }];
  vi.stubGlobal("XMLHttpRequest", NetworkXhr);
});
afterEach(() => vi.unstubAllGlobals());
describe("real Gateway XHR multipart recovery", () => {
  it("replays the file and idempotency key with the refreshed token", async () => {
    NetworkXhr.responses.push({ status: 200, body: { job: { job_id: "a", status: "queued" } } });
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh" }))
      .mockResolvedValueOnce(mockSharedSessionResponse());
    await submit();
    const [first, retry] = NetworkXhr.sent;
    expect(NetworkXhr.sent).toHaveLength(2);
    expect(first.headers.get("X-CSRF-Token")).toBe("stale");
    expect(retry.headers.get("X-CSRF-Token")).toBe("fresh");
    expect(retry.headers.get("Idempotency-Key")).toBe(first.headers.get("Idempotency-Key"));
    expect(Array.from((retry.body as FormData).entries())).toEqual(Array.from((first.body as FormData).entries()));
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it("surfaces a repeated rejection without a third upload", async () => {
    NetworkXhr.responses.push({ status: 403, body: csrfError });
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh" }))
      .mockResolvedValueOnce(mockSharedSessionResponse());
    await expect(submit()).rejects.toThrow();
    expect(NetworkXhr.sent).toHaveLength(2);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it("does not retry another authorization failure", async () => {
    NetworkXhr.responses = [{ status: 403, body: { error: { code: "AUTHORIZATION_ERROR", message: "Forbidden" } } }];
    await expect(submit()).rejects.toThrow();
    expect(NetworkXhr.sent).toHaveLength(1);
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each(["provider-a", "provider-b"])("does not upload into a replacement session for %s", async (userId) => {
    const auth = useAuthStore();
    const originalSession = auth.captureSession();
    NetworkXhr.responses.push({ status: 200, body: { job: { job_id: "wrong-owner", status: "queued" } } });
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ csrf_token: "replacement" }))
      .mockResolvedValueOnce(mockSharedSessionResponse("session-b", userId));
    await expect(submit()).rejects.toThrow();
    expect(NetworkXhr.sent).toHaveLength(1);
    expect(auth.user).toBeNull();
    expect(auth.isCurrentSession(originalSession)).toBe(false);
    expect(auth.csrfToken).toBeNull();
  });
  it("does not upload A's file as B after hydration", async () => {
    vi.mocked(fetch).mockImplementationOnce(async () => {
      const auth = useAuthStore();
      auth.clear();
      auth.user = createTestUser({ id: "B" });
      auth.csrfToken = "B-token";
      return mockJsonResponse({ csrf_token: "A-token" });
    });
    await expect(submit()).rejects.toBeInstanceOf(SupersededAuthSessionError);
    expect(NetworkXhr.sent).toHaveLength(1);
    expect(useAuthStore().csrfToken).toBe("B-token");
  });
});
