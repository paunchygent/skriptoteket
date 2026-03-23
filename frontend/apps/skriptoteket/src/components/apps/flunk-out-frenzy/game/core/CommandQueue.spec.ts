/**
 * Command queue tests for Flunk-Out Frenzy.
 *
 * These tests cover the small buffering contract that lets DOM input adapters
 * enqueue intent while the runtime loop drains commands at deterministic
 * boundaries.
 */

import { describe, expect, it } from "vitest";

import { CommandQueue } from "./CommandQueue";

describe("CommandQueue", () => {
  it("drains commands in insertion order", () => {
    const queue = new CommandQueue<string>();

    queue.push("left-down");
    queue.push("left-up");
    queue.push("launch");

    expect(queue.drain()).toEqual([
      "left-down",
      "left-up",
      "launch",
    ]);
  });

  it("returns an empty array after commands have already been drained", () => {
    const queue = new CommandQueue<string>();

    queue.push("left-down");

    expect(queue.drain()).toEqual(["left-down"]);
    expect(queue.drain()).toEqual([]);
  });

  it("clears queued commands before the next drain", () => {
    const queue = new CommandQueue<string>();

    queue.push("left-down");
    queue.push("right-down");
    queue.clear();

    expect(queue.drain()).toEqual([]);
  });
});
