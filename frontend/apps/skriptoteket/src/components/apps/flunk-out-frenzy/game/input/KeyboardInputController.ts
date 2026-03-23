/**
 * Keyboard-to-command adapter for Flunk-Out Frenzy.
 *
 * The host attaches this adapter to the browser window so input stays outside
 * Vue state and outside the runtime internals. It translates keyboard events
 * into runtime commands and leaves the simulation boundary in charge of
 * actually handling them.
 */

import type { RuntimeCommand } from "../core/runtimeTypes";

export interface RuntimeCommandSink {
  enqueueCommand(command: RuntimeCommand): void;
}

export interface KeyboardEventTargetLike {
  addEventListener(
    type: "keydown" | "keyup",
    listener: (event: KeyboardEvent) => void,
  ): void;
  removeEventListener(
    type: "keydown" | "keyup",
    listener: (event: KeyboardEvent) => void,
  ): void;
}

export class KeyboardInputController {
  private attached = false;

  constructor(
    private readonly commandSink: RuntimeCommandSink,
    private readonly eventTarget: KeyboardEventTargetLike = window,
  ) {}

  attach(): void {
    if (this.attached) {
      return;
    }

    this.attached = true;
    this.eventTarget.addEventListener("keydown", this.onKeyDown);
    this.eventTarget.addEventListener("keyup", this.onKeyUp);
  }

  detach(): void {
    if (!this.attached) {
      return;
    }

    this.attached = false;
    this.eventTarget.removeEventListener("keydown", this.onKeyDown);
    this.eventTarget.removeEventListener("keyup", this.onKeyUp);
  }

  private readonly onKeyDown = (event: KeyboardEvent): void => {
    const command = mapKeyboardEventToCommand(event, true);
    if (!command || event.repeat) {
      return;
    }

    event.preventDefault();
    this.commandSink.enqueueCommand(command);
  };

  private readonly onKeyUp = (event: KeyboardEvent): void => {
    const command = mapKeyboardEventToCommand(event, false);
    if (!command) {
      return;
    }

    event.preventDefault();
    this.commandSink.enqueueCommand(command);
  };
}

function mapKeyboardEventToCommand(
  event: KeyboardEvent,
  pressed: boolean,
): RuntimeCommand | null {
  if (event.code === "ShiftLeft") {
    return { type: "left-flip", pressed };
  }
  if (event.code === "ShiftRight") {
    return { type: "right-flip", pressed };
  }
  if (event.code === "Space") {
    return { type: "launch", pressed };
  }
  return null;
}
