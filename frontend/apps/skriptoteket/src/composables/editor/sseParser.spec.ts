import { describe, expect, it } from "vitest";

import { createSseParser } from "./sseParser";

describe("createSseParser", () => {
  it("parses events across chunk boundaries", () => {
    const parser = createSseParser();

    const first = parser.push("event: meta\ndata: {\"enabled\": true}\n");
    expect(first).toEqual([]);

    const second = parser.push("\n");
    expect(second).toEqual([
      { event: "meta", data: "{\"enabled\": true}" },
    ]);
  });

  it("merges multi-line data entries", () => {
    const parser = createSseParser();

    const events = parser.push(
      "event: delta\n" +
        "data: {\"text\": \"Hello\"}\n" +
        "data: {\"text\": \"World\"}\n\n",
    );

    expect(events).toEqual([
      {
        event: "delta",
        data: "{\"text\": \"Hello\"}\n{\"text\": \"World\"}",
      },
    ]);
  });
});
