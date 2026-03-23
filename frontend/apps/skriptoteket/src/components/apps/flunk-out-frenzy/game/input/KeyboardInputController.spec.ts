/**
 * Keyboard input adapter tests for Flunk-Out Frenzy.
 *
 * These tests ensure browser keyboard events are translated into runtime
 * commands instead of mutating Vue state directly.
 */

import { describe, expect, it } from "vitest";

import { KeyboardInputController } from "./KeyboardInputController";

describe("KeyboardInputController", () => {
  it("maps keyboard events to runtime commands", () => {
    const commands: Array<{ type: string; pressed: boolean }> = [];
    const controller = new KeyboardInputController({
      enqueueCommand(command) {
        commands.push(command);
      },
    });

    controller.attach();
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "ShiftLeft" }));
    window.dispatchEvent(new KeyboardEvent("keyup", { code: "ShiftLeft" }));
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "Space" }));
    controller.detach();

    expect(commands).toEqual([
      { type: "left-flip", pressed: true },
      { type: "left-flip", pressed: false },
      { type: "launch", pressed: true },
    ]);
  });

  it("ignores repeated keydown events so held keys do not spam commands", () => {
    const commands: Array<{ type: string; pressed: boolean }> = [];
    const controller = new KeyboardInputController({
      enqueueCommand(command) {
        commands.push(command);
      },
    });

    controller.attach();
    window.dispatchEvent(new KeyboardEvent("keydown", { code: "ShiftRight", repeat: true }));
    controller.detach();

    expect(commands).toEqual([]);
  });
});
