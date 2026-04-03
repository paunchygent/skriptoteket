/**
 * Keyboard input adapter tests for Flunk-Out Frenzy.
 *
 * These tests ensure browser keyboard events are translated into runtime
 * commands instead of mutating Vue state directly.
 */

import { describe, expect, it, vi } from "vitest";

import { KeyboardInputController } from "./KeyboardInputController";

class FakeKeyboardTarget {
  private keydownListener: ((event: KeyboardEvent) => void) | null = null;
  private keyupListener: ((event: KeyboardEvent) => void) | null = null;

  addEventListener(type: "keydown" | "keyup", listener: (event: KeyboardEvent) => void): void {
    if (type === "keydown") {
      this.keydownListener = listener;
      return;
    }
    this.keyupListener = listener;
  }

  removeEventListener(type: "keydown" | "keyup", listener: (event: KeyboardEvent) => void): void {
    if (type === "keydown" && this.keydownListener === listener) {
      this.keydownListener = null;
      return;
    }
    if (type === "keyup" && this.keyupListener === listener) {
      this.keyupListener = null;
    }
  }

  emitKeyDown(event: Partial<KeyboardEvent> & { code: string }): void {
    this.keydownListener?.(event as KeyboardEvent);
  }

  emitKeyUp(event: Partial<KeyboardEvent> & { code: string }): void {
    this.keyupListener?.(event as KeyboardEvent);
  }
}

class FakePointerTarget {
  private pointerDownListener: ((event: PointerEvent) => void) | null = null;
  private pointerUpListener: ((event: PointerEvent) => void) | null = null;
  private pointerCancelListener: ((event: PointerEvent) => void) | null = null;
  private lostPointerCaptureListener: ((event: PointerEvent) => void) | null = null;
  capturedPointerId: number | null = null;

  addEventListener(
    type: "pointerdown" | "pointerup" | "pointercancel" | "lostpointercapture",
    listener: (event: PointerEvent) => void,
  ): void {
    if (type === "pointerdown") {
      this.pointerDownListener = listener;
      return;
    }
    if (type === "pointerup") {
      this.pointerUpListener = listener;
      return;
    }
    if (type === "pointercancel") {
      this.pointerCancelListener = listener;
      return;
    }
    this.lostPointerCaptureListener = listener;
  }

  removeEventListener(
    type: "pointerdown" | "pointerup" | "pointercancel" | "lostpointercapture",
    listener: (event: PointerEvent) => void,
  ): void {
    if (type === "pointerdown" && this.pointerDownListener === listener) {
      this.pointerDownListener = null;
      return;
    }
    if (type === "pointerup" && this.pointerUpListener === listener) {
      this.pointerUpListener = null;
      return;
    }
    if (type === "pointercancel" && this.pointerCancelListener === listener) {
      this.pointerCancelListener = null;
      return;
    }
    if (type === "lostpointercapture" && this.lostPointerCaptureListener === listener) {
      this.lostPointerCaptureListener = null;
    }
  }

  setPointerCapture(pointerId: number): void {
    this.capturedPointerId = pointerId;
  }

  releasePointerCapture(pointerId: number): void {
    if (this.capturedPointerId === pointerId) {
      this.capturedPointerId = null;
    }
  }

  focus(): void {}

  emitPointerDown(event: Partial<PointerEvent> & { pointerId: number }): void {
    this.pointerDownListener?.(event as PointerEvent);
  }

  emitPointerUp(event: Partial<PointerEvent> & { pointerId: number }): void {
    this.pointerUpListener?.(event as PointerEvent);
  }
}

class FakeWindowTarget {
  private blurListener: (() => void) | null = null;

  addEventListener(type: "blur", listener: () => void): void {
    if (type === "blur") {
      this.blurListener = listener;
    }
  }

  removeEventListener(type: "blur", listener: () => void): void {
    if (type === "blur" && this.blurListener === listener) {
      this.blurListener = null;
    }
  }

  emitBlur(): void {
    this.blurListener?.();
  }
}

class FakeVisibilityTarget {
  visibilityState: DocumentVisibilityState = "visible";
  private visibilityChangeListener: (() => void) | null = null;

  addEventListener(type: "visibilitychange", listener: () => void): void {
    if (type === "visibilitychange") {
      this.visibilityChangeListener = listener;
    }
  }

  removeEventListener(type: "visibilitychange", listener: () => void): void {
    if (type === "visibilitychange" && this.visibilityChangeListener === listener) {
      this.visibilityChangeListener = null;
    }
  }

  setHidden(): void {
    this.visibilityState = "hidden";
    this.visibilityChangeListener?.();
  }
}

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
      { type: "launch", pressed: false },
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

  it("maps pointer hold/release on the playfield to launch commands", () => {
    const commands: Array<{ type: string; pressed: boolean }> = [];
    const keyboardTarget = new FakeKeyboardTarget();
    const pointerTarget = new FakePointerTarget();
    const windowTarget = new FakeWindowTarget();
    const visibilityTarget = new FakeVisibilityTarget();
    const controller = new KeyboardInputController(
      {
        enqueueCommand(command) {
          commands.push(command);
        },
      },
      keyboardTarget,
      pointerTarget,
      windowTarget,
      visibilityTarget,
    );

    controller.attach();
    pointerTarget.emitPointerDown({
      pointerId: 7,
      button: 0,
      preventDefault: vi.fn(),
    });
    pointerTarget.emitPointerUp({
      pointerId: 7,
      preventDefault: vi.fn(),
    });
    controller.detach();

    expect(pointerTarget.capturedPointerId).toBeNull();
    expect(commands).toEqual([
      { type: "launch", pressed: true },
      { type: "launch", pressed: false },
    ]);
  });

  it("releases pressed controls on window blur so launch cannot get stuck", () => {
    const commands: Array<{ type: string; pressed: boolean }> = [];
    const keyboardTarget = new FakeKeyboardTarget();
    const pointerTarget = new FakePointerTarget();
    const windowTarget = new FakeWindowTarget();
    const visibilityTarget = new FakeVisibilityTarget();
    const controller = new KeyboardInputController(
      {
        enqueueCommand(command) {
          commands.push(command);
        },
      },
      keyboardTarget,
      pointerTarget,
      windowTarget,
      visibilityTarget,
    );

    controller.attach();
    keyboardTarget.emitKeyDown({
      code: "ShiftLeft",
      repeat: false,
      preventDefault: vi.fn(),
    });
    keyboardTarget.emitKeyDown({
      code: "Space",
      repeat: false,
      preventDefault: vi.fn(),
    });
    windowTarget.emitBlur();
    controller.detach();

    expect(commands).toEqual([
      { type: "left-flip", pressed: true },
      { type: "launch", pressed: true },
      { type: "left-flip", pressed: false },
      { type: "launch", pressed: false },
    ]);
  });
});
