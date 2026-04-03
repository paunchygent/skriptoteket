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

export interface LaunchPointerTargetLike {
  addEventListener(
    type: "pointerdown" | "pointerup" | "pointercancel" | "lostpointercapture",
    listener: (event: PointerEvent) => void,
  ): void;
  removeEventListener(
    type: "pointerdown" | "pointerup" | "pointercancel" | "lostpointercapture",
    listener: (event: PointerEvent) => void,
  ): void;
  setPointerCapture?(pointerId: number): void;
  releasePointerCapture?(pointerId: number): void;
  focus?(options?: FocusOptions): void;
}

export interface WindowEventTargetLike {
  addEventListener(type: "blur", listener: () => void): void;
  removeEventListener(type: "blur", listener: () => void): void;
}

export interface VisibilityEventTargetLike {
  addEventListener(type: "visibilitychange", listener: () => void): void;
  removeEventListener(type: "visibilitychange", listener: () => void): void;
  visibilityState?: DocumentVisibilityState;
}

export class KeyboardInputController {
  private attached = false;
  private leftPressed = false;
  private rightPressed = false;
  private launchKeyboardPressed = false;
  private launchPointerPressed = false;
  private launchEffectivePressed = false;
  private activePointerId: number | null = null;
  private capturedPointerId: number | null = null;

  constructor(
    private readonly commandSink: RuntimeCommandSink,
    private readonly eventTarget: KeyboardEventTargetLike = window,
    private readonly launchTarget: LaunchPointerTargetLike | null = null,
    private readonly windowTarget: WindowEventTargetLike = window,
    private readonly visibilityTarget: VisibilityEventTargetLike = document,
  ) {}

  attach(): void {
    if (this.attached) {
      return;
    }

    this.attached = true;
    this.eventTarget.addEventListener("keydown", this.onKeyDown);
    this.eventTarget.addEventListener("keyup", this.onKeyUp);
    this.launchTarget?.addEventListener("pointerdown", this.onPointerDown);
    this.launchTarget?.addEventListener("pointerup", this.onPointerUp);
    this.launchTarget?.addEventListener("pointercancel", this.onPointerCancel);
    this.launchTarget?.addEventListener("lostpointercapture", this.onLostPointerCapture);
    this.windowTarget.addEventListener("blur", this.onWindowBlur);
    this.visibilityTarget.addEventListener("visibilitychange", this.onVisibilityChange);
  }

  detach(): void {
    if (!this.attached) {
      return;
    }

    this.attached = false;
    this.eventTarget.removeEventListener("keydown", this.onKeyDown);
    this.eventTarget.removeEventListener("keyup", this.onKeyUp);
    this.launchTarget?.removeEventListener("pointerdown", this.onPointerDown);
    this.launchTarget?.removeEventListener("pointerup", this.onPointerUp);
    this.launchTarget?.removeEventListener("pointercancel", this.onPointerCancel);
    this.launchTarget?.removeEventListener("lostpointercapture", this.onLostPointerCapture);
    this.windowTarget.removeEventListener("blur", this.onWindowBlur);
    this.visibilityTarget.removeEventListener("visibilitychange", this.onVisibilityChange);
    this.releaseAllPressedCommands();
  }

  private readonly onKeyDown = (event: KeyboardEvent): void => {
    const control = mapKeyboardEventToControl(event);
    if (!control || event.repeat) {
      return;
    }

    event.preventDefault();
    this.applyControlState(control, true, "keyboard");
  };

  private readonly onKeyUp = (event: KeyboardEvent): void => {
    const control = mapKeyboardEventToControl(event);
    if (!control) {
      return;
    }

    event.preventDefault();
    this.applyControlState(control, false, "keyboard");
  };

  private readonly onPointerDown = (event: PointerEvent): void => {
    if (event.button !== 0) {
      return;
    }
    if (this.activePointerId !== null && this.activePointerId !== event.pointerId) {
      return;
    }

    event.preventDefault();
    this.activePointerId = event.pointerId;
    this.capturedPointerId = event.pointerId;
    this.launchTarget?.setPointerCapture?.(event.pointerId);
    this.launchTarget?.focus?.({ preventScroll: true });
    this.applyControlState("launch", true, "pointer");
  };

  private readonly onPointerUp = (event: PointerEvent): void => {
    if (this.activePointerId !== event.pointerId) {
      return;
    }
    event.preventDefault();
    this.releaseCapturedPointer(event.pointerId);
    this.activePointerId = null;
    this.applyControlState("launch", false, "pointer");
  };

  private readonly onPointerCancel = (event: PointerEvent): void => {
    if (this.activePointerId !== event.pointerId) {
      return;
    }
    this.releaseCapturedPointer(event.pointerId);
    this.activePointerId = null;
    this.applyControlState("launch", false, "pointer");
  };

  private readonly onLostPointerCapture = (event: PointerEvent): void => {
    if (this.capturedPointerId === event.pointerId) {
      this.capturedPointerId = null;
    }
    if (this.activePointerId !== event.pointerId) {
      return;
    }
    this.activePointerId = null;
    this.applyControlState("launch", false, "pointer");
  };

  private readonly onWindowBlur = (): void => {
    this.releaseAllPressedCommands();
  };

  private readonly onVisibilityChange = (): void => {
    if (this.visibilityTarget.visibilityState === "hidden") {
      this.releaseAllPressedCommands();
    }
  };

  private applyControlState(
    control: KeyboardControl,
    pressed: boolean,
    source: "keyboard" | "pointer",
  ): void {
    if (control === "left-flip") {
      if (this.leftPressed === pressed) {
        return;
      }
      this.leftPressed = pressed;
      this.commandSink.enqueueCommand({ type: "left-flip", pressed });
      return;
    }

    if (control === "right-flip") {
      if (this.rightPressed === pressed) {
        return;
      }
      this.rightPressed = pressed;
      this.commandSink.enqueueCommand({ type: "right-flip", pressed });
      return;
    }

    if (source === "keyboard") {
      this.launchKeyboardPressed = pressed;
    } else {
      this.launchPointerPressed = pressed;
    }
    this.syncLaunchPressedCommand();
  }

  private syncLaunchPressedCommand(): void {
    const nextLaunchPressed = this.launchKeyboardPressed || this.launchPointerPressed;
    if (nextLaunchPressed === this.launchEffectivePressed) {
      return;
    }
    this.launchEffectivePressed = nextLaunchPressed;
    this.commandSink.enqueueCommand({
      type: "launch",
      pressed: nextLaunchPressed,
    });
  }

  private releaseAllPressedCommands(): void {
    if (this.leftPressed) {
      this.leftPressed = false;
      this.commandSink.enqueueCommand({ type: "left-flip", pressed: false });
    }
    if (this.rightPressed) {
      this.rightPressed = false;
      this.commandSink.enqueueCommand({ type: "right-flip", pressed: false });
    }
    this.launchKeyboardPressed = false;
    this.launchPointerPressed = false;
    this.syncLaunchPressedCommand();
    this.releaseCapturedPointer(this.activePointerId);
    this.activePointerId = null;
  }

  private releaseCapturedPointer(pointerId: number | null): void {
    if (pointerId === null) {
      return;
    }
    if (this.capturedPointerId !== pointerId) {
      return;
    }
    this.launchTarget?.releasePointerCapture?.(pointerId);
    this.capturedPointerId = null;
  }
}

type KeyboardControl = "left-flip" | "right-flip" | "launch";

function mapKeyboardEventToControl(event: KeyboardEvent): KeyboardControl | null {
  if (event.code === "ShiftLeft") {
    return "left-flip";
  }
  if (event.code === "ShiftRight") {
    return "right-flip";
  }
  if (event.code === "Space") {
    return "launch";
  }
  return null;
}
