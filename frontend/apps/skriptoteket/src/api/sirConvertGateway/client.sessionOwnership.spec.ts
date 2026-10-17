import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SupersededAuthSessionError, useAuthStore } from "../../stores/auth";
import { createTestProfile, createTestUser, mockJsonResponse } from "../../stores/authTestHelpers";
import { cancelTranscriptJob, downloadTranscriptJson, getTranscriptJob, getTranscriptResult,
  listTranscriptArtifacts, submitTranscriptJob } from "./client";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
function admit(id: string, csrfToken: string | null = `${id}-csrf`) {
  const auth = useAuthStore();
  auth.clear();
  auth.$patch({ user: createTestUser({ id }), profile: createTestProfile({ user_id: id }), csrfToken,
    grants: [`${id}-grant`], featureFlags: [`${id}-flag`], bootstrapped: true });
  return auth;
}
function uploadFile() {
  const file = new File(["audio"], "lesson.m4a", { type: "audio/mp4" });
  Object.defineProperty(file, "arrayBuffer", { value: async () => new ArrayBuffer(5), configurable: true });
  return file;
}
const params = { jobId: "job-a", correlationId: "corr-a" };
const job = { job: { job_id: "job-a", status: "queued" } };

// This fake replaces only the browser's XHR network boundary, not the Gateway adapter,
// request preparation, auth store, CSRF loader, headers or multipart transport.
class NetworkXhr {
  static sends = vi.fn();
  static autoRespond = false;
  static instances: NetworkXhr[] = [];
  upload = { onprogress: null as null | ((event: ProgressEvent) => void) };
  onload: null | (() => void) = null;
  onerror: null | (() => void) = null;
  onabort: null | (() => void) = null;
  status = 200;
  statusText = "OK";
  responseText = JSON.stringify(job);
  withCredentials = false;
  headers = new Headers();
  constructor() { NetworkXhr.instances.push(this); }
  open() {}
  setRequestHeader(key: string, value: string) { this.headers.set(key, value); }
  getAllResponseHeaders() { return "content-type: application/json"; }
  send(body: unknown) {
    NetworkXhr.sends(body);
    if (NetworkXhr.autoRespond) queueMicrotask(() => this.onload?.());
  }
  abort() { this.onabort?.(); }
}

beforeEach(() => {
  setActivePinia(createPinia());
  vi.mocked(fetch).mockReset();
  NetworkXhr.sends.mockReset();
  NetworkXhr.autoRespond = false;
  NetworkXhr.instances = [];
  vi.stubGlobal("XMLHttpRequest", NetworkXhr);
  admit("teacher-a");
});
afterEach(() => { vi.unstubAllGlobals(); });

describe.each([false, true])("real browser Gateway upload, multipart=%s", (multipart) => {
  it("rejects A superseded during asynchronous file preparation before either network transport", async () => {
    NetworkXhr.autoRespond = true;
    const bytes = deferred<ArrayBuffer>();
    const file = uploadFile();
    Object.defineProperty(file, "arrayBuffer", { value: () => bytes.promise });
    vi.mocked(fetch).mockResolvedValue(mockJsonResponse(job));
    const result = submitTranscriptJob({ file, correlationId: "corr-a", speakerControl: { mode: "auto" },
      ...(multipart ? { onUploadProgress: vi.fn() } : {}) }).catch((error: unknown) => error);
    await flushPromises();
    const auth = admit("teacher-b");
    const expected = JSON.parse(JSON.stringify(auth.$state));
    bytes.resolve(new ArrayBuffer(5));
    expect(await result).toBeInstanceOf(SupersededAuthSessionError);
    expect(fetch).not.toHaveBeenCalled();
    expect(NetworkXhr.sends).not.toHaveBeenCalled();
    expect(auth.$state).toEqual(expected);
  });

  it("rejects A superseded during real CSRF hydration without sending its file as B", async () => {
    NetworkXhr.autoRespond = true;
    admit("teacher-a", null);
    const csrf = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(csrf.promise).mockResolvedValue(mockJsonResponse(job));
    const result = submitTranscriptJob({ file: uploadFile(), correlationId: "corr-a", speakerControl: { mode: "auto" },
      ...(multipart ? { onUploadProgress: vi.fn() } : {}) }).catch((error: unknown) => error);
    await vi.waitFor(() => expect(fetch).toHaveBeenCalledOnce());
    expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain("/auth/csrf");
    const auth = admit("teacher-b");
    const expected = JSON.parse(JSON.stringify(auth.$state));
    csrf.resolve(mockJsonResponse({ csrf_token: "a-delayed-csrf" }));
    expect(await result).toBeInstanceOf(SupersededAuthSessionError);
    expect(fetch).toHaveBeenCalledOnce();
    expect(NetworkXhr.sends).not.toHaveBeenCalled();
    expect(auth.$state).toEqual(expected);
  });

  it("does not admit a delayed upload response belonging to A after B takes over", async () => {
    const response = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(response.promise);
    const result = submitTranscriptJob({ file: uploadFile(), correlationId: "corr-a", speakerControl: { mode: "auto" },
      ...(multipart ? { onUploadProgress: vi.fn() } : {}) }).catch((error: unknown) => error);
    await vi.waitFor(() => expect(multipart ? NetworkXhr.sends : fetch).toHaveBeenCalledOnce());
    const auth = admit("teacher-b");
    const expected = JSON.parse(JSON.stringify(auth.$state));
    if (multipart) NetworkXhr.instances[0].onload?.();
    else response.resolve(mockJsonResponse(job));
    expect(await result).toBeInstanceOf(SupersededAuthSessionError);
    expect(auth.$state).toEqual(expected);
  });
});

const reads = [
  { name: "status", request: getTranscriptJob, payload: job },
  { name: "result", request: getTranscriptResult, payload: { api_version: "v2", job_id: "job-a", result: {
    artifact: { filename: "transcript.json", content_type: "application/json", sha256: "abc", size_bytes: 5 },
    conversion_metadata: { pipeline_used: "audio_to_transcript_bundle_v2", backend_used: "stt_sidecar", acceleration_used: "rocm", options_fingerprint: "fp" },
  } } },
  { name: "artifacts", request: listTranscriptArtifacts, payload: { api_version: "v2", job_id: "job-a", output_format: "transcript_bundle", artifacts: [
    { artifact_key: "transcript_json", filename: "transcript.json", content_type: "application/json", availability: "available", size_bytes: 5, sha256: "abc", retrieval_path: "/jobs/job-a/artifacts/transcript_json" },
  ] } },
  { name: "JSON", request: downloadTranscriptJson, payload: { schema_version: "transcript_json_v1", transcript: { text: "A private text", segments: [
    { id: "seg_1", start_seconds: 0, end_seconds: 1, speaker_label: "SPEAKER_00", text: "A private text" },
  ] }, diarization: { status: "succeeded", used_mode: "auto" }, alignment: { status: "succeeded" } } },
  { name: "cancellation", request: cancelTranscriptJob, payload: job },
];

describe.each(reads)("real browser Gateway $name", ({ request, payload }) => {
  it("rejects a superseded response instead of returning A's data to B", async () => {
    const response = deferred<Response>();
    vi.mocked(fetch).mockReturnValueOnce(response.promise);
    const result = request(params).catch((error: unknown) => error);
    await flushPromises();
    expect(fetch).toHaveBeenCalledOnce();
    const auth = admit("teacher-b");
    const expected = JSON.parse(JSON.stringify(auth.$state));
    response.resolve(mockJsonResponse(payload));
    expect(await result).toBeInstanceOf(SupersededAuthSessionError);
    expect(auth.$state).toEqual(expected);
  });
});

it("never sends a superseded cancellation after its real CSRF request returns", async () => {
  admit("teacher-a", null);
  const csrf = deferred<Response>();
  vi.mocked(fetch).mockReturnValueOnce(csrf.promise).mockResolvedValue(mockJsonResponse(job));
  const result = cancelTranscriptJob(params).catch((error: unknown) => error);
  expect(fetch).toHaveBeenCalledOnce();
  admit("teacher-b");
  csrf.resolve(mockJsonResponse({ csrf_token: "a-delayed-csrf" }));
  expect(await result).toBeInstanceOf(SupersededAuthSessionError);
  expect(fetch).toHaveBeenCalledOnce();
});

it("rejects a status response superseded while its JSON body is being read", async () => {
  const body = deferred<unknown>();
  const response = mockJsonResponse(job);
  const json = vi.spyOn(response, "json").mockReturnValue(body.promise);
  vi.mocked(fetch).mockResolvedValue(response);
  const result = getTranscriptJob(params).catch((error: unknown) => error);
  await vi.waitFor(() => expect(json).toHaveBeenCalledOnce());
  admit("teacher-b");
  body.resolve(job);
  expect(await result).toBeInstanceOf(SupersededAuthSessionError);
});
