/**
 * Room touch viewport gesture composable.
 *
 * This composable translates two-finger phone classroom-map gestures into the
 * shared room viewport zoom model while letting each map surface keep ownership
 * of its domain-specific tap, placement, selection, and drag behavior.
 */

import { ref } from "vue";

type TouchPoint = {
  clientX: number;
  clientY: number;
};

export type RoomTouchViewportGestureOptions = {
  onZoomByFactor: (factor: number) => void;
  onGestureStart?: () => void;
  onGestureEnd?: () => void;
};

function touchDistance(first: TouchPoint, second: TouchPoint): number {
  return Math.hypot(first.clientX - second.clientX, first.clientY - second.clientY);
}

function firstTwoTouches(event: TouchEvent): [TouchPoint, TouchPoint] | null {
  const first = event.touches.item(0);
  const second = event.touches.item(1);
  return first && second ? [first, second] : null;
}

export function useRoomTouchViewportGestures(options: RoomTouchViewportGestureOptions) {
  const gestureActive = ref(false);
  const suppressNextTap = ref(false);
  let lastDistance: number | null = null;

  function beginGesture(event: TouchEvent): void {
    const touches = firstTwoTouches(event);
    if (!touches) {
      return;
    }
    lastDistance = touchDistance(touches[0], touches[1]);
    gestureActive.value = true;
    suppressNextTap.value = true;
    options.onGestureStart?.();
    event.preventDefault();
  }

  function handleTouchStart(event: TouchEvent): void {
    if (event.touches.length >= 2) {
      beginGesture(event);
    }
  }

  function handleTouchMove(event: TouchEvent): void {
    if (!gestureActive.value || event.touches.length < 2) {
      return;
    }
    const touches = firstTwoTouches(event);
    if (!touches || lastDistance === null) {
      return;
    }
    const nextDistance = touchDistance(touches[0], touches[1]);
    if (lastDistance > 0 && nextDistance > 0) {
      options.onZoomByFactor(nextDistance / lastDistance);
    }
    lastDistance = nextDistance;
    suppressNextTap.value = true;
    event.preventDefault();
  }

  function endGesture(): void {
    if (gestureActive.value) {
      options.onGestureEnd?.();
    }
    gestureActive.value = false;
    lastDistance = null;
  }

  function handleTouchEnd(event: TouchEvent): void {
    if (event.touches.length < 2) {
      endGesture();
    }
  }

  function handleTouchCancel(): void {
    endGesture();
  }

  function consumeTapSuppression(): boolean {
    if (!suppressNextTap.value) {
      return false;
    }
    suppressNextTap.value = false;
    return true;
  }

  return {
    gestureActive,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    handleTouchCancel,
    consumeTapSuppression,
  };
}
