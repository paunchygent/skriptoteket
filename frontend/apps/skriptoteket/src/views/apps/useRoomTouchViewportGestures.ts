/**
 * Room touch viewport gesture composable.
 *
 * This composable translates two-finger phone classroom-map gestures into the
 * shared room viewport zoom model while letting each map surface keep ownership
 * of its domain-specific tap, placement, selection, and drag behavior.
 */

import { onBeforeUnmount, ref, watch, type Ref } from "vue";

type TouchPoint = {
  clientX: number;
  clientY: number;
};

export type RoomTouchViewportGestureAnchor = {
  clientX: number;
  clientY: number;
};

export type RoomTouchViewportGestureOptions = {
  onZoomByFactor: (factor: number, anchor: RoomTouchViewportGestureAnchor | null) => void;
  onGestureStart?: (anchor: RoomTouchViewportGestureAnchor | null) => void;
  onGestureEnd?: () => void;
  target?: Ref<HTMLElement | null>;
};

type PlatformGestureEvent = Event & { clientX?: number; clientY?: number; scale?: number };

function touchDistance(first: TouchPoint, second: TouchPoint): number {
  return Math.hypot(first.clientX - second.clientX, first.clientY - second.clientY);
}

function touchMidpoint(
  first: TouchPoint,
  second: TouchPoint,
): RoomTouchViewportGestureAnchor {
  return {
    clientX: (first.clientX + second.clientX) / 2,
    clientY: (first.clientY + second.clientY) / 2,
  };
}

function firstTwoTouches(event: TouchEvent): [TouchPoint, TouchPoint] | null {
  const first = event.touches.item(0);
  const second = event.touches.item(1);
  return first && second ? [first, second] : null;
}

function preventBrowserDefault(event: Event): void {
  if (event.cancelable) {
    event.preventDefault();
  }
}

function platformGestureScale(event: Event): number | null {
  const scale = (event as PlatformGestureEvent).scale;
  return typeof scale === "number" && Number.isFinite(scale) && scale > 0 ? scale : null;
}

function platformGestureAnchor(event: Event): RoomTouchViewportGestureAnchor | null {
  const gestureEvent = event as PlatformGestureEvent;
  return typeof gestureEvent.clientX === "number"
    && typeof gestureEvent.clientY === "number"
    && Number.isFinite(gestureEvent.clientX)
    && Number.isFinite(gestureEvent.clientY)
    ? { clientX: gestureEvent.clientX, clientY: gestureEvent.clientY }
    : null;
}

export function useRoomTouchViewportGestures(options: RoomTouchViewportGestureOptions) {
  const gestureActive = ref(false);
  const suppressNextTap = ref(false);
  let lastDistance: number | null = null;
  let platformGestureActive = false;
  let lastPlatformGestureScale: number | null = null;
  let cleanupTarget: (() => void) | null = null;

  function beginGesture(event: TouchEvent): void {
    if (platformGestureActive) {
      preventBrowserDefault(event);
      return;
    }
    const touches = firstTwoTouches(event);
    if (!touches) {
      return;
    }
    lastDistance = touchDistance(touches[0], touches[1]);
    const anchor = touchMidpoint(touches[0], touches[1]);
    gestureActive.value = true;
    suppressNextTap.value = true;
    options.onGestureStart?.(anchor);
    preventBrowserDefault(event);
  }

  function handleTouchStart(event: TouchEvent): void {
    if (event.touches.length >= 2) {
      beginGesture(event);
    }
  }

  function handleTouchMove(event: TouchEvent): void {
    if (platformGestureActive) {
      preventBrowserDefault(event);
      return;
    }
    if (!gestureActive.value || event.touches.length < 2) {
      return;
    }
    const touches = firstTwoTouches(event);
    if (!touches || lastDistance === null) {
      return;
    }
    const nextDistance = touchDistance(touches[0], touches[1]);
    if (lastDistance > 0 && nextDistance > 0) {
      options.onZoomByFactor(nextDistance / lastDistance, touchMidpoint(touches[0], touches[1]));
    }
    lastDistance = nextDistance;
    suppressNextTap.value = true;
    preventBrowserDefault(event);
  }

  function handlePlatformGestureStart(event: Event): void {
    lastPlatformGestureScale = platformGestureScale(event) ?? 1;
    const anchor = platformGestureAnchor(event);
    platformGestureActive = true;
    gestureActive.value = true;
    suppressNextTap.value = true;
    lastDistance = null;
    options.onGestureStart?.(anchor);
    preventBrowserDefault(event);
  }

  function handlePlatformGestureChange(event: Event): void {
    const nextScale = platformGestureScale(event);
    if (nextScale === null) {
      return;
    }
    if (!platformGestureActive) {
      handlePlatformGestureStart(event);
    }
    if (lastPlatformGestureScale !== null && lastPlatformGestureScale > 0) {
      options.onZoomByFactor(
        nextScale / lastPlatformGestureScale,
        platformGestureAnchor(event),
      );
    }
    lastPlatformGestureScale = nextScale;
    suppressNextTap.value = true;
    preventBrowserDefault(event);
  }

  function endGesture(): void {
    if (gestureActive.value) {
      options.onGestureEnd?.();
    }
    gestureActive.value = false;
    platformGestureActive = false;
    lastDistance = null;
    lastPlatformGestureScale = null;
  }

  function handleTouchEnd(event: TouchEvent): void {
    if (event.touches.length < 2) {
      endGesture();
    }
  }

  function handleTouchCancel(): void {
    endGesture();
  }

  function bindGestureTarget(element: HTMLElement): () => void {
    const listenerOptions = { passive: false };
    element.addEventListener("touchstart", handleTouchStart, listenerOptions);
    element.addEventListener("touchmove", handleTouchMove, listenerOptions);
    element.addEventListener("touchend", handleTouchEnd, listenerOptions);
    element.addEventListener("touchcancel", handleTouchCancel, listenerOptions);
    element.addEventListener("gesturestart", handlePlatformGestureStart, listenerOptions);
    element.addEventListener("gesturechange", handlePlatformGestureChange, listenerOptions);
    element.addEventListener("gestureend", handleTouchCancel, listenerOptions);
    return () => {
      element.removeEventListener("touchstart", handleTouchStart);
      element.removeEventListener("touchmove", handleTouchMove);
      element.removeEventListener("touchend", handleTouchEnd);
      element.removeEventListener("touchcancel", handleTouchCancel);
      element.removeEventListener("gesturestart", handlePlatformGestureStart);
      element.removeEventListener("gesturechange", handlePlatformGestureChange);
      element.removeEventListener("gestureend", handleTouchCancel);
    };
  }

  if (options.target) {
    watch(
      options.target,
      (target, _previousTarget, onCleanup) => {
        cleanupTarget?.();
        cleanupTarget = null;
        if (!target) {
          return;
        }
        const cleanup = bindGestureTarget(target);
        cleanupTarget = cleanup;
        onCleanup(() => {
          cleanup();
          if (cleanupTarget === cleanup) {
            cleanupTarget = null;
          }
        });
      },
      { flush: "sync", immediate: true },
    );
    onBeforeUnmount(() => {
      cleanupTarget?.();
      cleanupTarget = null;
    });
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
    handlePlatformGestureStart,
    handlePlatformGestureChange,
    consumeTapSuppression,
  };
}
