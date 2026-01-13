import { createSseParser, type SseEvent } from "../sseParser";

type ChatStreamDeltaEvent = {
  kind: "delta";
  text: string;
};

type ChatStreamMetaEvent = {
  kind: "meta";
  assistantMessageId?: string;
  turnId?: string;
  correlationId?: string;
};

type ChatStreamNoticeEvent = {
  kind: "notice";
  message: string;
  variant?: "info" | "warning";
};

type ChatStreamDoneEvent = {
  kind: "done";
  enabled?: boolean;
  reason?: string;
  message?: string;
  code?: string;
};

type ChatStreamEvent =
  | ChatStreamDeltaEvent
  | ChatStreamMetaEvent
  | ChatStreamNoticeEvent
  | ChatStreamDoneEvent;

type ChatStreamResult = {
  sawDelta: boolean;
  sawDone: boolean;
};

function parseChatStreamEvent(event: SseEvent): ChatStreamEvent | null {
  let payload: unknown;
  try {
    payload = JSON.parse(event.data);
  } catch {
    return null;
  }

  if (!payload || typeof payload !== "object") {
    return null;
  }

  switch (event.event) {
    case "delta": {
      const text = String((payload as { text?: string }).text ?? "");
      if (!text) return null;
      return { kind: "delta", text };
    }
    case "meta": {
      const meta = payload as {
        assistant_message_id?: string;
        turn_id?: string;
        correlation_id?: string;
      };
      return {
        kind: "meta",
        assistantMessageId: meta.assistant_message_id,
        turnId: meta.turn_id,
        correlationId: meta.correlation_id,
      };
    }
    case "notice": {
      const message = String((payload as { message?: string }).message ?? "").trim();
      if (!message) return null;
      const variant = String((payload as { variant?: string }).variant ?? "info");
      return {
        kind: "notice",
        message,
        variant: variant === "warning" ? "warning" : "info",
      };
    }
    case "done": {
      const donePayload = payload as {
        enabled?: boolean;
        reason?: string;
        message?: string;
        code?: string;
      };
      return {
        kind: "done",
        enabled: typeof donePayload.enabled === "boolean" ? donePayload.enabled : undefined,
        reason: donePayload.reason,
        message: donePayload.message,
        code: donePayload.code,
      };
    }
    default:
      return null;
  }
}

export async function consumeChatStream(params: {
  response: Response;
  signal: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
}): Promise<ChatStreamResult> {
  const { response, signal, onEvent } = params;
  if (!response.body) {
    return { sawDelta: false, sawDone: false };
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  const parser = createSseParser();
  let sawDelta = false;
  let sawDone = false;

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    if (signal.aborted) {
      continue;
    }

    const chunk = decoder.decode(value, { stream: true });
    const events = parser.push(chunk);
    for (const event of events) {
      if (signal.aborted) {
        break;
      }

      const parsed = parseChatStreamEvent(event);
      if (!parsed) {
        continue;
      }

      if (parsed.kind === "delta") {
        sawDelta = true;
      }
      if (parsed.kind === "done") {
        sawDone = true;
      }

      onEvent(parsed);
    }
  }

  return { sawDelta, sawDone };
}

export type { ChatStreamEvent, ChatStreamResult };
