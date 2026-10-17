import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SupersededAuthSessionError, useAuthStore } from "../../stores/auth";
import { createTestUser, mockJsonResponse } from "../../stores/authTestHelpers";
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
beforeEach(() => {
  setActivePinia(createPinia());
  vi.mocked(fetch).mockReset();
  const auth = useAuthStore();
  auth.user = createTestUser();
  auth.csrfToken = "stale";
  NetworkXhr.sent = [];
  NetworkXhr.responses = [{ status: 403, body: csrfError }];
  vi.stubGlobal("XMLHttpRequest", NetworkXhr);
});
afterEach(() => vi.unstubAllGlobals());
describe("real Gateway XHR multipart recovery", () => {
  it("replays the file and idempotency key with the refreshed token", async () => {
    NetworkXhr.responses.push({ status: 200, body: { job: { job_id: "a", status: "queued" } } });
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh" }));
    await submit();
    const [first, retry] = NetworkXhr.sent;
    expect(NetworkXhr.sent).toHaveLength(2);
    expect(first.headers.get("X-CSRF-Token")).toBe("stale");
    expect(retry.headers.get("X-CSRF-Token")).toBe("fresh");
    expect(retry.headers.get("Idempotency-Key")).toBe(first.headers.get("Idempotency-Key"));
    expect(Array.from((retry.body as FormData).entries())).toEqual(Array.from((first.body as FormData).entries()));
    expect(fetch).toHaveBeenCalledOnce();
  });
  it("surfaces a repeated rejection without a third upload", async () => {
    NetworkXhr.responses.push({ status: 403, body: csrfError });
    vi.mocked(fetch).mockResolvedValueOnce(mockJsonResponse({ csrf_token: "fresh" }));
    await expect(submit()).rejects.toThrow();
    expect(NetworkXhr.sent).toHaveLength(2);
    expect(fetch).toHaveBeenCalledOnce();
  });
  it("does not retry another authorization failure", async () => {
    NetworkXhr.responses = [{ status: 403, body: { error: { code: "AUTHORIZATION_ERROR", message: "Forbidden" } } }];
    await expect(submit()).rejects.toThrow();
    expect(NetworkXhr.sent).toHaveLength(1);
    expect(fetch).not.toHaveBeenCalled();
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
