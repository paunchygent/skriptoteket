import { describe, expect, it, vi, afterEach } from "vitest";
import { ref } from "vue";
import { createPinia, setActivePinia } from "pinia";

import { apiFetch } from "../../api/client";
import { useAuthStore } from "../../stores/auth";
import { useEditorChat } from "./useEditorChat";

const originalFetch = global.fetch;

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

afterEach(() => {
  vi.restoreAllMocks();
  if (originalFetch) {
    global.fetch = originalFetch;
  }
});

describe("useEditorChat", () => {
  it("shows a partial warning when the stream ends with done.reason=error after deltas", async () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.user = {
      id: "user-1",
      email: "user@example.com",
      role: "contributor",
      auth_provider: "local",
      external_id: null,
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    };
    auth.csrfToken = "csrf";

    const { stream, push, close } = createControlledStream();
    global.fetch = vi.fn().mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { error, messages, sendMessage } = useEditorChat({ toolId, baseVersionId });

    const sendPromise = sendMessage("Hej");

    push("event: meta\ndata: {\"enabled\": true}\n\n");
    push("event: delta\ndata: {\"text\": \"Hej\"}\n\n");
    push("event: done\ndata: {\"enabled\": true, \"reason\": \"error\"}\n\n");
    close();

    await sendPromise;

    expect(messages.value.length).toBe(2);
    expect(messages.value[1].content).toBe("Hej");
    expect(error.value).toContain("ofullständigt");
  });

  it("shows an error when the stream ends with done.reason=error before any deltas", async () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.user = {
      id: "user-1",
      email: "user@example.com",
      role: "contributor",
      auth_provider: "local",
      external_id: null,
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    };
    auth.csrfToken = "csrf";

    const { stream, push, close } = createControlledStream();
    global.fetch = vi.fn().mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { error, messages, sendMessage } = useEditorChat({ toolId, baseVersionId });

    const sendPromise = sendMessage("Hej");

    push("event: meta\ndata: {\"enabled\": true}\n\n");
    push("event: done\ndata: {\"enabled\": true, \"reason\": \"error\"}\n\n");
    close();

    await sendPromise;

    expect(messages.value.length).toBe(1);
    expect(error.value).toContain("läsa");
  });

  it("cancels a stream without applying late deltas", async () => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.user = {
      id: "user-1",
      email: "user@example.com",
      role: "contributor",
      auth_provider: "local",
      external_id: null,
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    };
    auth.csrfToken = "csrf";

    const { stream, push, close } = createControlledStream();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    global.fetch = fetchMock;

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { messages, streaming, sendMessage, cancel } = useEditorChat({ toolId, baseVersionId });

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
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.user = {
      id: "user-1",
      email: "user@example.com",
      role: "contributor",
      auth_provider: "local",
      external_id: null,
      is_active: true,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
    };
    auth.csrfToken = "csrf";

    vi.mocked(apiFetch).mockResolvedValueOnce(undefined);

    const toolId = ref("tool-1");
    const baseVersionId = ref<string | null>(null);
    const { messages, streaming, clear } = useEditorChat({ toolId, baseVersionId });

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
});
