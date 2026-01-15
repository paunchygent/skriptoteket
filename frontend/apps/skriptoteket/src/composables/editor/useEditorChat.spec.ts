import { afterEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import { createPinia, setActivePinia } from "pinia";

import { apiFetch } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import { useEditorChat } from "./useEditorChat";

const originalFetch = globalThis.fetch;

vi.mock("../../api/client", () => ({
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  isApiError: (error: unknown) => error instanceof Error,
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
    external_id: null,
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

describe("useEditorChat", () => {
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
    const allowRemoteFallback = ref(false);
    const { error, messages, sendMessage } = useEditorChat({
      toolId,
      baseVersionId,
      allowRemoteFallback,
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
    const allowRemoteFallback = ref(false);
    const { error, messages, sendMessage } = useEditorChat({
      toolId,
      baseVersionId,
      allowRemoteFallback,
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
    const allowRemoteFallback = ref(false);
    const { disabledMessage, messages, sendMessage } = useEditorChat({
      toolId,
      baseVersionId,
      allowRemoteFallback,
    });

    const sendPromise = sendMessage("Hej");

    push(
      "event: meta\ndata: {\"enabled\": true, \"correlation_id\": \"corr-123\", \"turn_id\": \"turn-123\", \"assistant_message_id\": \"assistant-123\"}\n\n",
    );
    push(
      "event: done\ndata: {\"enabled\": false, \"message\": \"Den lokala AI-modellen är inte tillgänglig.\", \"code\": \"remote_fallback_required\"}\n\n",
    );
    close();

    await sendPromise;

    expect(disabledMessage.value).toBeNull();
    expect(messages.value.length).toBe(2);
    expect(messages.value[1].role).toBe("assistant");
    expect(messages.value[1].content).toContain("Den lokala AI-modellen");
    expect(messages.value[1].correlationId).toBe("corr-123");
    expect(messages.value[1].status).toBe("failed");
    expect(messages.value[1].failureOutcome).toBe("remote_fallback_required");
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
    const allowRemoteFallback = ref(false);
    const { messages, streaming, sendMessage, cancel } = useEditorChat({
      toolId,
      baseVersionId,
      allowRemoteFallback,
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
    const allowRemoteFallback = ref(false);
    const { messages, streaming, clear } = useEditorChat({
      toolId,
      baseVersionId,
      allowRemoteFallback,
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
    const allowRemoteFallback = ref(false);
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
      allowRemoteFallback,
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
    expect(payload.allow_remote_fallback).toBe(false);
    expect(payload.base_version_id).toBe("version-1");
    expect(payload.active_file).toBe("tool.py");
    expect(payload.virtual_files).toEqual(virtualFiles.value);
  });
});
