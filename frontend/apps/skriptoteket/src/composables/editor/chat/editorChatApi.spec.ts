import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch, apiGet } from "../../../api/client";
import { clearChatHistory, fetchChatHistory, postChatStream, readChatErrorMessage } from "./editorChatApi";

const originalFetch = globalThis.fetch;

vi.mock("../../../api/client", () => ({
  apiFetch: vi.fn(),
  apiGet: vi.fn(),
}));

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
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    globalThis.fetch = fetchMock;

    const controller = new AbortController();

    await postChatStream({
      toolId: "tool/1",
      body: { message: "Hi", allow_remote_fallback: false },
      correlationId: "corr-1",
      csrfToken: "csrf-1",
      signal: controller.signal,
    });

    const call = fetchMock.mock.calls[0];
    expect(call?.[0]).toBe("/api/v1/editor/tools/tool%2F1/chat");
    const init = call?.[1] as RequestInit | undefined;
    const headers = new Headers(init?.headers);
    expect(headers.get("Accept")).toBe("text/event-stream");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-CSRF-Token")).toBe("csrf-1");
    expect(headers.get("X-Correlation-ID")).toBe("corr-1");
    expect(init?.credentials).toBe("include");
    expect(init?.method).toBe("POST");
  });

  it("reads error messages from json payloads", async () => {
    const response = new Response(JSON.stringify({ error: { message: "Nope" } }), {
      status: 400,
      headers: { "content-type": "application/json" },
    });

    const message = await readChatErrorMessage(response);

    expect(message).toBe("Nope");
  });

  it("falls back to validation error when detail is present", async () => {
    const response = new Response(JSON.stringify({ detail: { field: "message" } }), {
      status: 422,
      headers: { "content-type": "application/json" },
    });

    const message = await readChatErrorMessage(response);

    expect(message).toBe("Validation error");
  });
});
