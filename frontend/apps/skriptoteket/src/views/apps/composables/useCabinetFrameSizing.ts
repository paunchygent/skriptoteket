import { computed, onBeforeUnmount, onMounted, ref, type Ref } from "vue";

export function useCabinetFrameSizing(sceneElement: Ref<HTMLElement | null>) {
  // The physics board is 600x1200, but the surrounding cabinet frame is
  // intentionally wider so the shell reads as a full cabinet instead of a narrow
  // portrait slit on laptop/desktop viewports.
  const CABINET_FRAME_ASPECT_RATIO = 0.72;
  const DESKTOP_BREAKPOINT_PX = 940;
  const DESKTOP_HORIZONTAL_MARGIN_PX = 24;
  const DESKTOP_BOTTOM_RESERVE_PX = 24;

  const hostFrame = ref<{
    width: number | null;
    height: number | null;
  }>({
    width: null,
    height: null,
  });

  let sceneResizeObserver: ResizeObserver | null = null;
  let scheduledFrameReflowHandle: number | null = null;
  let deferredFrameReflowHandle: number | null = null;

  const hostFrameStyle = computed(() => {
    if (hostFrame.value.width === null || hostFrame.value.height === null) {
      return {};
    }

    return {
      width: `${hostFrame.value.width}px`,
      height: `${hostFrame.value.height}px`,
    };
  });

  function updateBoardFrame(): void {
    const scene = sceneElement.value;
    if (!scene || typeof window === "undefined") {
      return;
    }

    if (window.innerWidth <= DESKTOP_BREAKPOINT_PX) {
      hostFrame.value = { width: null, height: null };
      return;
    }

    const sceneStyles = window.getComputedStyle(scene);
    const sceneRect = scene.getBoundingClientRect();
    const paddingX =
      parseFloat(sceneStyles.paddingLeft) + parseFloat(sceneStyles.paddingRight);

    const availableWidth = Math.max(
      scene.clientWidth - paddingX - DESKTOP_HORIZONTAL_MARGIN_PX,
      320,
    );
    const viewportHeightBudget = Math.max(
      window.innerHeight - sceneRect.top - DESKTOP_BOTTOM_RESERVE_PX,
      220,
    );
    const availableHeight = viewportHeightBudget;

    const width = Math.floor(
      Math.min(availableWidth, availableHeight * CABINET_FRAME_ASPECT_RATIO),
    );
    const height = Math.floor(width / CABINET_FRAME_ASPECT_RATIO);

    hostFrame.value = { width, height };
  }

  function clearScheduledBoardFrameUpdates(): void {
    if (typeof window === "undefined") {
      return;
    }

    if (scheduledFrameReflowHandle !== null) {
      window.cancelAnimationFrame(scheduledFrameReflowHandle);
      scheduledFrameReflowHandle = null;
    }

    if (deferredFrameReflowHandle !== null) {
      window.clearTimeout(deferredFrameReflowHandle);
      deferredFrameReflowHandle = null;
    }
  }

  function scheduleBoardFrameUpdate(): void {
    if (typeof window === "undefined") {
      return;
    }

    clearScheduledBoardFrameUpdates();
    scheduledFrameReflowHandle = window.requestAnimationFrame(() => {
      updateBoardFrame();
      scheduledFrameReflowHandle = null;
    });

    deferredFrameReflowHandle = window.setTimeout(() => {
      updateBoardFrame();
      deferredFrameReflowHandle = null;
    }, 250);
  }

  onMounted(() => {
    if (typeof window !== "undefined" && typeof ResizeObserver !== "undefined") {
      sceneResizeObserver = new ResizeObserver(() => {
        scheduleBoardFrameUpdate();
      });

      if (sceneElement.value) {
        sceneResizeObserver.observe(sceneElement.value);
      }

      window.addEventListener("resize", scheduleBoardFrameUpdate);
      scheduleBoardFrameUpdate();
    }
  });

  onBeforeUnmount(() => {
    if (typeof window !== "undefined") {
      window.removeEventListener("resize", scheduleBoardFrameUpdate);
    }

    if (sceneResizeObserver) {
      sceneResizeObserver.disconnect();
      sceneResizeObserver = null;
    }

    clearScheduledBoardFrameUpdates();
  });

  return {
    hostFrame,
    hostFrameStyle,
    updateBoardFrame,
  };
}
