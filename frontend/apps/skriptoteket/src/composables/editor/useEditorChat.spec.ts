import { afterEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import { createPinia, setActivePinia } from "pinia";

import { apiFetch } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import { createTestProfile, createTestUser, mockJsonResponse, mockSharedSessionResponse } from "../../stores/authTestHelpers";
import { useEditorChat } from "./useEditorChat";

const originalFetch = globalThis.fetch;

vi.mock("../../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../../api/client")>(),
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  isApiError: (error: unknown) => error instanceof Error,
  resolveProtectedApiUrl: vi.fn((path: string) => path),
}));

function createControlledStream() {
  let controller: ReadableStreamDefaultController<Uint8Array> | null = null;
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(ctrl) {
      controller = ctrl;
    },
  });

  return {
    stream,
    push(text: string) {
      controller?.enqueue(encoder.encode(text));
    },
    close() {
      controller?.close();
    },
  };
}

async function flushPromises(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0));
}

function setupAuth(): void {
  setActivePinia(createPinia());
  const auth = useAuthStore();
  auth.user = {
    id: "user-1",
    email: "user@example.com",
    email_verified: true,
    role: "contributor",
    auth_provider: "local",
    is_active: true,
    failed_login_attempts: 0,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
  };
  auth.csrfToken = "csrf";
}

afterEach(() => {
  vi.restoreAllMocks();
  if (originalFetch) {
    globalThis.fetch = originalFetch;
  }
});

function deferredResponse() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((done) => { resolve = done; });
  return { promise, resolve };
}

function admitReplacementTeacher() {
  const auth = useAuthStore();
  auth.clear();
  auth.$patch({
    user: createTestUser({ id: "teacher-b" }),
    profile: createTestProfile({ user_id: "teacher-b", display_name: "B", exam_courses: {
      school_forms: ["grundskolan"], course_keys: ["B-course"],
    } }),
    sharedSessionId: "session-b",
    csrfToken: "B-csrf",
    grants: ["B-grant"], featureFlags: ["B-flag"],
  });
  return JSON.parse(JSON.stringify(auth.$state));
}

describe("useEditorChat", () => {
  it("still expires the originating session on its own chat 401 (positive control)", async () => {
    setupAuth();
    globalThis.fetch = vi.fn().mockResolvedValueOnce(mockJsonResponse({
      error: { code: "UNAUTHORIZED", message: "Session expired" },
    }, 401));
    const chat = useEditorChat({ toolId: ref("tool-1"), baseVersionId: ref(null) });
    await chat.sendMessage("Hej");
    expect(useAuthStore().user).toBeNull();
    expect(useAuthStore().csrfToken).toBeNull();
    expect(chat.streaming.value).toBe(false);
    expect(chat.messages.value.at(-1)).toMatchObject({
      role: "assistant", content: "Session expired", status: "failed",
    });
  });

  it.each([400, 401])("does not render A's delayed %s error body in B's session", async (status) => {
    setupAuth();
    let resolveBody!: (value: unknown) => void;
    const body = new Promise<unknown>((done) => { resolveBody = done; });
    const response = mockJsonResponse({}, status);
    const readBody = vi.spyOn(response, "json").mockReturnValueOnce(body);
    globalThis.fetch = vi.fn().mockResolvedValueOnce(response);
    const chat = useEditorChat({ toolId: ref("tool-1"), baseVersionId: ref(null) });
    const sending = chat.sendMessage("A's message");
    await flushPromises();
    expect(readBody).toHaveBeenCalledOnce();
    const expected = admitReplacementTeacher();
    const messagesBefore = JSON.parse(JSON.stringify(chat.messages.value));
    resolveBody({ error: { code: "OLD_ERROR", message: "A-only error body" } });
    await sending;
    expect(useAuthStore().$state).toEqual(expected);
    expect(chat.messages.value).toEqual(messagesBefore);
    expect(chat.streaming.value).toBe(false);
  });

  it("does not expire B when A's delayed chat response is 401", async () => {
    setupAuth();
    const pending = deferredResponse();
    globalThis.fetch = vi.fn().mockReturnValueOnce(pending.promise);
    const chat = useEditorChat({ toolId: ref("tool-1"), baseVersionId: ref(null) });
    const sending = chat.sendMessage("A's message");
    await flushPromises();
    expect(fetch).toHaveBeenCalledOnce();
    const expected = admitReplacementTeacher();
    pending.resolve(mockJsonResponse({ detail: "A expired" }, 401));
    await sending;
    expect(useAuthStore().$state).toEqual(expected);
  });

  it.each(["csrf", "session"] as const)(
    "never sends A's chat body after B is admitted during the %s acquisition step",
    async (step) => {
      setupAuth();
      const auth = useAuthStore();
      auth.sharedSessionId = "session-a";
      auth.csrfToken = null;
      const pending = deferredResponse();
      let markStarted!: () => void;
      const started = new Promise<void>((resolve) => { markStarted = resolve; });
      globalThis.fetch = vi.fn(async (input) => {
        const path = new URL(String(input)).pathname;
        if (path === `/v1/auth/${step}`) {
          markStarted();
          return pending.promise;
        }
        if (path === "/v1/auth/csrf") return mockJsonResponse({ csrf_token: "A-csrf" });
        return mockJsonResponse({ detail: "must not dispatch" }, 400);
      });
      const chat = useEditorChat({ toolId: ref("tool-1"), baseVersionId: ref(null) });
      const sending = chat.sendMessage("A's private message");
      await started;
      const expected = admitReplacementTeacher();
      pending.resolve(step === "csrf"
        ? mockJsonResponse({ csrf_token: "A-csrf" })
        : mockSharedSessionResponse("session-a"));
      await sending;
      const requests = vi.mocked(fetch).mock.calls.map(([input, init]) => ({
        path: new URL(String(input)).pathname,
        method: init?.method,
        body: init?.body,
      }));
      expect(requests).toEqual((step === "csrf" ? ["csrf"] : ["csrf", "session"])
        .map((endpoint) => ({ path: `/v1/auth/${endpoint}`, method: "GET", body: undefined })));
      expect(useAuthStore().$state).toEqual(expected);
      expect(chat.streaming.value).toBe(false);
    },
  );
  it("shows a partial warning when the stream ends with done.reason=error after deltas", async () => {
    setupAuth();

    const { stream, push, close } = createControlledStream();
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { error, messages, sendMessage } = useEditorChat({
      toolId,
      baseVersionId,
    });

    const sendPromise = sendMessage("Hej");

    push("event: meta\ndata: {\"enabled\": true}\n\n");
    push("event: delta\ndata: {\"text\": \"Hej\"}\n\n");
    push("event: done\ndata: {\"enabled\": true, \"reason\": \"error\"}\n\n");
    close();

    await sendPromise;

    expect(messages.value.length).toBe(2);
    expect(messages.value[1].content).toContain("Hej");
    expect(messages.value[1].content).toContain("ofullständigt");
    expect(error.value).toBeNull();
  });

  it("shows an error when the stream ends with done.reason=error before any deltas", async () => {
    setupAuth();

    const { stream, push, close } = createControlledStream();
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { error, messages, sendMessage } = useEditorChat({
      toolId,
      baseVersionId,
    });

    const sendPromise = sendMessage("Hej");

    push("event: meta\ndata: {\"enabled\": true}\n\n");
    push("event: done\ndata: {\"enabled\": true, \"reason\": \"error\"}\n\n");
    close();

    await sendPromise;

    expect(messages.value.length).toBe(2);
    expect(messages.value[1].content).toContain("läsa");
    expect(error.value).toBeNull();
  });

  it("creates an assistant message for disabled responses and preserves correlation-id", async () => {
    setupAuth();

    const { stream, push, close } = createControlledStream();
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { messages, sendMessage } = useEditorChat({
      toolId,
      baseVersionId,
    });

    const sendPromise = sendMessage("Hej");

    push(
      "event: meta\ndata: {\"enabled\": true, \"correlation_id\": \"corr-123\", \"turn_id\": \"turn-123\", \"assistant_message_id\": \"assistant-123\"}\n\n",
    );
    push(
      "event: done\ndata: {\"enabled\": false, \"message\": \"Den lokala AI-modellen är inte tillgänglig.\", \"code\": \"model_unavailable\"}\n\n",
    );
    close();

    await sendPromise;

    expect(messages.value.length).toBe(2);
    expect(messages.value[1].role).toBe("assistant");
    expect(messages.value[1].content).toContain("Den lokala AI-modellen");
    expect(messages.value[1].correlationId).toBe("corr-123");
    expect(messages.value[1].status).toBe("failed");
    expect(messages.value[1].failureOutcome).toBe("model_unavailable");
  });

  it("cancels a stream without applying late deltas", async () => {
    setupAuth();

    const { stream, push, close } = createControlledStream();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    globalThis.fetch = fetchMock;

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { messages, streaming, sendMessage, cancel } = useEditorChat({
      toolId,
      baseVersionId,
    });

    const sendPromise = sendMessage("Hej");

    push("event: meta\ndata: {\"enabled\": true}\n\n");
    push("event: delta\ndata: {\"text\": \"Hej\"}\n\n");
    await flushPromises();

    cancel();

    push("event: delta\ndata: {\"text\": \" senare\"}\n\n");
    close();

    await sendPromise;

    expect(streaming.value).toBe(false);
    expect(messages.value.length).toBe(2);
    expect(messages.value[1].content).toBe("Hej");
  });

  it("clears the chat and issues a delete", async () => {
    setupAuth();

    vi.mocked(apiFetch).mockResolvedValueOnce(undefined);

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { messages, streaming, clear } = useEditorChat({
      toolId,
      baseVersionId,
    });

    messages.value = [
      {
        id: "msg-1",
        role: "user",
        content: "Hej",
        createdAt: "2025-01-01T00:00:00Z",
      },
    ];
    streaming.value = true;

    await clear();

    expect(apiFetch).toHaveBeenCalledWith("/api/v1/editor/tools/tool-1/chat", {
      method: "DELETE",
    });
    expect(messages.value).toEqual([]);
    expect(streaming.value).toBe(false);
  });

  it("keeps a question sent while the chat is still being cleared", async () => {
    setupAuth();

    let finishDelete!: () => void;
    vi.mocked(apiFetch).mockImplementationOnce(
      () => new Promise<undefined>((done) => { finishDelete = () => done(undefined); }),
    );
    const { stream, push, close } = createControlledStream();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(stream, { status: 200, headers: { "Content-Type": "text/event-stream" } }),
    );
    globalThis.fetch = fetchMock;

    const { messages, clear, sendMessage } = useEditorChat({
      toolId: ref("tool-1"),
      baseVersionId: ref<string | null>(null),
    });
    messages.value = [
      { id: "old-1", role: "user", content: "Gammal fråga", createdAt: "2025-01-01T00:00:00Z" },
    ];

    const clearPromise = clear();
    const sendPromise = sendMessage("Ny fråga");
    await flushPromises();
    expect(fetchMock).not.toHaveBeenCalled();

    finishDelete();
    await clearPromise;
    await flushPromises();
    push("event: meta\ndata: {\"enabled\": true}\n\n");
    push("event: done\ndata: {\"enabled\": true, \"reason\": \"stop\"}\n\n");
    close();
    await sendPromise;

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(messages.value.map((message) => message.content)).toContain("Ny fråga");
    expect(messages.value.map((message) => message.content)).not.toContain("Gammal fråga");
  });

  it("includes active_file + virtual_files in the chat request when provided", async () => {
    setupAuth();

    const { stream, push, close } = createControlledStream();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    globalThis.fetch = fetchMock;

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>("version-1");
    const activeFile = ref<"tool.py">("tool.py");
    const virtualFiles = ref({
      "tool.py": "print('hi')\n",
      "entrypoint.txt": "run_tool\n",
      "settings_schema.json": "{\n  \"type\": \"object\"\n}\n",
      "input_schema.json": "{\n  \"type\": \"array\"\n}\n",
      "usage_instructions.md": "Do the thing\n",
    });

    const { sendMessage } = useEditorChat({
      toolId,
      baseVersionId,
      activeFile,
      virtualFiles,
    });

    const sendPromise = sendMessage("Hej");

    push("event: meta\ndata: {\"enabled\": true}\n\n");
    push("event: done\ndata: {\"enabled\": true, \"reason\": \"stop\"}\n\n");
    close();

    await sendPromise;

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(init?.body).toBeTruthy();

    const payload = JSON.parse(String(init?.body ?? "")) as Record<string, unknown>;
    expect(payload.message).toBe("Hej");
    expect(payload.base_version_id).toBe("version-1");
    expect(payload.active_file).toBe("tool.py");
    expect(payload.virtual_files).toEqual(virtualFiles.value);
  });
});
