/**
 * Document Converter preview touch gesture owner.
 *
 * Domain purpose:
 *   Claim browser-level preview pinch gestures on the PDF viewport while
 *   leaving one-finger panning to the scroll container.
 *
 * Relationships:
 *   - Binds native non-passive listeners directly on `DocumentConverterResultPanel.vue`.
 *   - Feeds midpoint anchors into `useAnchoredDocumentPreviewZoom.ts`.
 */

import { onBeforeUnmount, watch, type Ref } from "vue";

type TouchPoint = {
  clientX: number;
  clientY: number;
};

export type DocumentPreviewGestureAnchor = {
  clientX: number;
  clientY: number;
};

export type UseDocumentPreviewTouchGesturesOptions = {
  onZoomByFactor: (
    factor: number,
    anchor: DocumentPreviewGestureAnchor | null,
  ) => void;
  onGestureStart?: (anchor: DocumentPreviewGestureAnchor | null) => void;
  onGestureEnd?: () => void;
  target: Ref<HTMLElement | null>;
};

type PlatformGestureEvent = Event & { clientX?: number; clientY?: number; scale?: number };

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

function touchDistance(first: TouchPoint, second: TouchPoint): number {
  return Math.hypot(first.clientX - second.clientX, first.clientY - second.clientY);
}

function touchMidpoint(
  first: TouchPoint,
  second: TouchPoint,
): DocumentPreviewGestureAnchor {
  return {
    clientX: (first.clientX + second.clientX) / 2,
    clientY: (first.clientY + second.clientY) / 2,
  };
}

function platformGestureAnchor(event: Event): DocumentPreviewGestureAnchor | null {
  const gestureEvent = event as PlatformGestureEvent;
  return typeof gestureEvent.clientX === "number"
    && typeof gestureEvent.clientY === "number"
    && Number.isFinite(gestureEvent.clientX)
    && Number.isFinite(gestureEvent.clientY)
    ? {
      clientX: gestureEvent.clientX,
      clientY: gestureEvent.clientY,
    }
    : null;
}

function platformGestureScale(event: Event): number | null {
  const scale = (event as PlatformGestureEvent).scale;
  return typeof scale === "number" && Number.isFinite(scale) && scale > 0 ? scale : null;
}

export function useDocumentPreviewTouchGestures(
  options: UseDocumentPreviewTouchGesturesOptions,
) {
  let cleanupTarget: (() => void) | null = null;
  let gestureActive = false;
  let lastDistance: number | null = null;
  let lastPlatformScale: number | null = null;
  let platformGestureActive = false;

  function endGesture(): void {
    if (gestureActive) {
      options.onGestureEnd?.();
    }
    gestureActive = false;
    platformGestureActive = false;
    lastDistance = null;
    lastPlatformScale = null;
  }

  function handleTouchStart(event: TouchEvent): void {
    const touches = firstTwoTouches(event);
    if (!touches) {
      return;
    }
    gestureActive = true;
    platformGestureActive = false;
    lastPlatformScale = null;
    lastDistance = touchDistance(touches[0], touches[1]);
    options.onGestureStart?.(touchMidpoint(touches[0], touches[1]));
    preventBrowserDefault(event);
  }

  function handleTouchMove(event: TouchEvent): void {
    if (platformGestureActive || !gestureActive) {
      if (platformGestureActive) {
        preventBrowserDefault(event);
      }
      return;
    }
    const touches = firstTwoTouches(event);
    if (!touches || lastDistance === null) {
      return;
    }
    const nextDistance = touchDistance(touches[0], touches[1]);
    if (lastDistance > 0 && nextDistance > 0) {
      options.onZoomByFactor(
        nextDistance / lastDistance,
        touchMidpoint(touches[0], touches[1]),
      );
    }
    lastDistance = nextDistance;
    preventBrowserDefault(event);
  }

  function handleTouchEnd(event: TouchEvent): void {
    if (event.touches.length < 2) {
      endGesture();
    }
  }

  function handlePlatformGestureStart(event: Event): void {
    gestureActive = true;
    platformGestureActive = true;
    lastDistance = null;
    lastPlatformScale = platformGestureScale(event) ?? 1;
    options.onGestureStart?.(platformGestureAnchor(event));
    preventBrowserDefault(event);
  }

  function handlePlatformGestureChange(event: Event): void {
    const nextScale = platformGestureScale(event);
    if (nextScale === null) {
      return;
    }
    if (!platformGestureActive) {
      handlePlatformGestureStart(event);
      return;
    }
    if (lastPlatformScale !== null && lastPlatformScale > 0) {
      options.onZoomByFactor(
        nextScale / lastPlatformScale,
        platformGestureAnchor(event),
      );
    }
    lastPlatformScale = nextScale;
    preventBrowserDefault(event);
  }

  function handlePlatformGestureEnd(event: Event): void {
    endGesture();
    preventBrowserDefault(event);
  }

  function handleTouchCancel(): void {
    endGesture();
  }

  function bindTarget(element: HTMLElement): () => void {
    const listenerOptions = { passive: false };
    element.addEventListener("touchstart", handleTouchStart, listenerOptions);
    element.addEventListener("touchmove", handleTouchMove, listenerOptions);
    element.addEventListener("touchend", handleTouchEnd, listenerOptions);
    element.addEventListener("touchcancel", handleTouchCancel, listenerOptions);
    element.addEventListener("gesturestart", handlePlatformGestureStart, listenerOptions);
    element.addEventListener("gesturechange", handlePlatformGestureChange, listenerOptions);
    element.addEventListener("gestureend", handlePlatformGestureEnd, listenerOptions);
    return () => {
      element.removeEventListener("touchstart", handleTouchStart);
      element.removeEventListener("touchmove", handleTouchMove);
      element.removeEventListener("touchend", handleTouchEnd);
      element.removeEventListener("touchcancel", handleTouchCancel);
      element.removeEventListener("gesturestart", handlePlatformGestureStart);
      element.removeEventListener("gesturechange", handlePlatformGestureChange);
      element.removeEventListener("gestureend", handlePlatformGestureEnd);
    };
  }

  watch(
    options.target,
    (target, _previousTarget, onCleanup) => {
      cleanupTarget?.();
      cleanupTarget = null;
      if (!target) {
        return;
      }
      const cleanup = bindTarget(target);
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

  return {
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    handleTouchCancel,
    handlePlatformGestureChange,
    handlePlatformGestureEnd,
    handlePlatformGestureStart,
  };
}
