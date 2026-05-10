/**
 * Room touch viewport gesture tests.
 *
 * These tests keep two-finger phone classroom-map gestures separate from the
 * one-finger domain actions owned by each map component.
 */

import { describe, expect, it, vi } from "vitest";

import { useRoomTouchViewportGestures } from "./useRoomTouchViewportGestures";

function touchEvent(distance: number, touches = 2): TouchEvent {
  const event = {
    touches: {
      length: touches,
      item: (index: number) => {
        if (index >= touches) {
          return null;
        }
        return {
          clientX: index === 0 ? 0 : distance,
          clientY: 0,
        };
      },
    },
    cancelable: true,
    preventDefault: vi.fn(),
  };
  return event as unknown as TouchEvent;
}

function platformGestureEvent(scale: number): Event {
  const event = new Event("gesturechange", { cancelable: true });
  Object.defineProperty(event, "scale", { value: scale });
  vi.spyOn(event, "preventDefault");
  return event;
}

describe("useRoomTouchViewportGestures", () => {
  it("turns pinch distance changes into zoom factors and suppresses the next tap", () => {
    const onZoomByFactor = vi.fn();
    const onGestureStart = vi.fn();
    const onGestureEnd = vi.fn();
    const gestures = useRoomTouchViewportGestures({
      onZoomByFactor,
      onGestureStart,
      onGestureEnd,
    });
    const start = touchEvent(100);
    const move = touchEvent(125);

    gestures.handleTouchStart(start);
    gestures.handleTouchMove(move);
    gestures.handleTouchEnd(touchEvent(125, 1));

    expect(onGestureStart).toHaveBeenCalledTimes(1);
    expect(onZoomByFactor).toHaveBeenCalledWith(1.25);
    expect(onGestureEnd).toHaveBeenCalledTimes(1);
    expect(start.preventDefault).toHaveBeenCalledOnce();
    expect(move.preventDefault).toHaveBeenCalledOnce();
    expect(gestures.consumeTapSuppression()).toBe(true);
    expect(gestures.consumeTapSuppression()).toBe(false);
  });

  it("ignores one-finger touch starts", () => {
    const onZoomByFactor = vi.fn();
    const gestures = useRoomTouchViewportGestures({ onZoomByFactor });

    gestures.handleTouchStart(touchEvent(100, 1));
    gestures.handleTouchMove(touchEvent(125, 1));

    expect(onZoomByFactor).not.toHaveBeenCalled();
    expect(gestures.consumeTapSuppression()).toBe(false);
  });

  it("turns platform gesture scale changes into zoom factors", () => {
    const onZoomByFactor = vi.fn();
    const gestures = useRoomTouchViewportGestures({ onZoomByFactor });
    const start = platformGestureEvent(1);
    const change = platformGestureEvent(1.2);

    gestures.handlePlatformGestureStart(start);
    gestures.handlePlatformGestureChange(change);
    gestures.handleTouchCancel();

    expect(onZoomByFactor).toHaveBeenCalledWith(1.2);
    expect(start.preventDefault).toHaveBeenCalledOnce();
    expect(change.preventDefault).toHaveBeenCalledOnce();
    expect(gestures.consumeTapSuppression()).toBe(true);
  });
});
