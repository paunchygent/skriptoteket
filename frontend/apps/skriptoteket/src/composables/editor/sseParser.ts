export type SseEvent = {
  event: string;
  data: string;
};

export type SseParser = {
  push: (chunk: string) => SseEvent[];
  reset: () => void;
};

function parseEvent(raw: string): SseEvent | null {
  const lines = raw.split("\n");
  let event = "message";
  const data: string[] = [];

  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      data.push(line.slice(5).trimStart());
    }
  }

  if (data.length === 0) {
    return null;
  }

  return { event: event || "message", data: data.join("\n") };
}

export function createSseParser(): SseParser {
  let buffer = "";

  function push(chunk: string): SseEvent[] {
    buffer += chunk;
    buffer = buffer.replace(/\r\n/g, "\n");

    const events: SseEvent[] = [];

    while (true) {
      const boundary = buffer.indexOf("\n\n");
      if (boundary < 0) {
        break;
      }
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      const parsed = parseEvent(raw);
      if (parsed) {
        events.push(parsed);
      }
    }

    return events;
  }

  function reset(): void {
    buffer = "";
  }

  return { push, reset };
}
