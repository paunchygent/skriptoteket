import { describe, expect, it } from "vitest";

import { consumeChatStream } from "./editorChatStreamClient";

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

describe("consumeChatStream", () => {
  it("emits delta and done events", async () => {
    const { stream, push, close } = createControlledStream();
    const events: unknown[] = [];
    const controller = new AbortController();
    const response = new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });

    const resultPromise = consumeChatStream({
      response,
      signal: controller.signal,
      onEvent: (event) => events.push(event),
    });

    push("event: delta\ndata: {\"text\": \"Hi\"}\n\n");
    push("event: done\ndata: {\"enabled\": true, \"reason\": \"stop\"}\n\n");
    close();

    const result = await resultPromise;

    expect(events).toHaveLength(2);
    expect(events[0]).toMatchObject({ kind: "delta", text: "Hi" });
    expect(events[1]).toMatchObject({ kind: "done", enabled: true, reason: "stop" });
    expect(result).toEqual({ sawDelta: true, sawDone: true });
  });

  it("ignores invalid json and normalizes notice variants", async () => {
    const { stream, push, close } = createControlledStream();
    const events: unknown[] = [];
    const controller = new AbortController();
    const response = new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });

    const resultPromise = consumeChatStream({
      response,
      signal: controller.signal,
      onEvent: (event) => events.push(event),
    });

    push("event: delta\ndata: not-json\n\n");
    push("event: notice\ndata: {\"message\": \"Heads up\", \"variant\": \"warning\"}\n\n");
    close();

    const result = await resultPromise;

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ kind: "notice", message: "Heads up", variant: "warning" });
    expect(result).toEqual({ sawDelta: false, sawDone: false });
  });

  it("skips events after abort", async () => {
    const { stream, push, close } = createControlledStream();
    const events: unknown[] = [];
    const controller = new AbortController();
    const response = new Response(stream, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });

    const resultPromise = consumeChatStream({
      response,
      signal: controller.signal,
      onEvent: (event) => events.push(event),
    });

    push("event: delta\ndata: {\"text\": \"Hello\"}\n\n");
    await flushPromises();
    controller.abort();
    push("event: delta\ndata: {\"text\": \"World\"}\n\n");
    close();

    await resultPromise;

    expect(events).toHaveLength(1);
    expect(events[0]).toMatchObject({ kind: "delta", text: "Hello" });
  });
});
