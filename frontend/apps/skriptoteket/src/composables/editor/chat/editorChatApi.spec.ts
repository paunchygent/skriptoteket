import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useAuthStore } from "../../../stores/auth";
import { createTestUser } from "../../../stores/authTestHelpers";

import { apiFetch, apiGet, resolveProtectedApiUrl } from "../../../api/client";
import { clearChatHistory, fetchChatHistory, postChatStream } from "./editorChatApi";

const originalFetch = globalThis.fetch;

vi.mock("../../../api/client", async (importOriginal) => ({
  ...await importOriginal<typeof import("../../../api/client")>(),
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
  resolveProtectedApiUrl: vi.fn((path: string) => path),
}));

beforeEach(() => {
  setActivePinia(createPinia());
  const auth = useAuthStore();
  auth.user = createTestUser();
  auth.csrfToken = "csrf-1";
});

afterEach(() => {
  vi.restoreAllMocks();
  if (originalFetch) {
    globalThis.fetch = originalFetch;
  }
});

describe("editorChatApi", () => {
  it("fetches chat history with encoded tool id and limit", async () => {
    vi.mocked(apiGet).mockResolvedValueOnce({ messages: [] });

    await fetchChatHistory("tool/1", 5);

    expect(apiGet).toHaveBeenCalledWith("/api/v1/editor/tools/tool%2F1/chat?limit=5");
  });

  it("clears chat history via delete", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(undefined);

    await clearChatHistory("tool/1");

    expect(apiFetch).toHaveBeenCalledWith("/api/v1/editor/tools/tool%2F1/chat", {
      method: "DELETE",
    });
  });

  it("posts chat stream with csrf + correlation headers", async () => {
    vi.mocked(resolveProtectedApiUrl).mockReturnValueOnce(
      "https://api.hule.education/api/v1/editor/tools/tool%2F1/chat",
    );
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(null, { status: 200 }));
    globalThis.fetch = fetchMock;

    const controller = new AbortController();

    await postChatStream({
      toolId: "tool/1",
      body: { message: "Hi" },
      correlationId: "corr-1",
      signal: controller.signal,
    });

    const call = fetchMock.mock.calls[0];
    expect(resolveProtectedApiUrl).toHaveBeenCalledWith("/api/v1/editor/tools/tool%2F1/chat");
    expect(call?.[0]).toBe("https://api.hule.education/api/v1/editor/tools/tool%2F1/chat");
    const init = call?.[1];
    const headers = new Headers(init?.headers);
    expect(headers.get("Accept")).toBe("text/event-stream");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-CSRF-Token")).toBe("csrf-1");
    expect(headers.get("X-Correlation-ID")).toBe("corr-1");
    expect(init?.credentials).toBe("include");
    expect(init?.method).toBe("POST");
  });
});
