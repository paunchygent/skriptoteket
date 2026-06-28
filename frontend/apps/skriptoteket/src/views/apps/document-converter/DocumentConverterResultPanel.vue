<script setup lang="ts">
/**
 * Result preview panel for the Document Converter route.
 *
 * Domain purpose:
 *   Show the active session result preview while leaving file operations and
 *   output selection to the shared middle-column controls.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Receives derived state from `useDocumentConverterSessionHistory`.
 *   - Leaves teacher actions to the operations-column controls.
 */
import { onBeforeUnmount, ref, watch } from "vue";

import { IconFitView, IconZoomIn, IconZoomOut } from "../../../components/icons";
import { useAnchoredDocumentPreviewZoom } from "./useAnchoredDocumentPreviewZoom";
import { useDocumentPreviewTouchGestures } from "./useDocumentPreviewTouchGestures";

const props = defineProps<{
  activePreviewUrl: string | null;
  resultTitle: string;
  resultStateLabel: string;
}>();

const previewViewport = ref<HTMLElement | null>(null);
const zoom = useAnchoredDocumentPreviewZoom(previewViewport, {
  resetSource: () => props.activePreviewUrl,
});

useDocumentPreviewTouchGestures({
  target: previewViewport,
  onZoomByFactor: zoom.zoomByFactor,
  onGestureStart: zoom.beginGestureCamera,
  onGestureEnd: zoom.endGestureCamera,
});

let resizeObserver: ResizeObserver | null = null;

function disconnectResizeObserver(): void {
  resizeObserver?.disconnect();
  resizeObserver = null;
}

watch(
  previewViewport,
  (element, _previousElement, onCleanup) => {
    disconnectResizeObserver();
    if (!element || typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }
      zoom.setViewportSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    observer.observe(element);
    resizeObserver = observer;
    onCleanup(() => {
      observer.disconnect();
      if (resizeObserver === observer) {
        resizeObserver = null;
      }
    });
  },
  { flush: "post", immediate: true },
);

onBeforeUnmount(() => {
  disconnectResizeObserver();
});
</script>

<template>
  <section
    class="dc-preview"
    aria-label="Resultat"
  >
    <header class="dc-preview-header">
      <h2>{{ resultTitle }}</h2>
      <div
        v-if="activePreviewUrl"
        class="dc-preview-toolbar"
        aria-label="Förhandsvisningens zoom"
      >
        <button
          type="button"
          class="dc-icon-button"
          data-testid="document-converter-preview-zoom-out"
          aria-label="Zooma ut"
          title="Zooma ut"
          @click="zoom.zoomOut"
        >
          <IconZoomOut :size="16" />
        </button>
        <span
          class="dc-preview-zoom-label"
          data-testid="document-converter-preview-zoom-label"
          aria-live="polite"
        >
          {{ zoom.scalePercent.value }}%
        </span>
        <button
          type="button"
          class="dc-icon-button"
          data-testid="document-converter-preview-zoom-in"
          aria-label="Zooma in"
          title="Zooma in"
          @click="zoom.zoomIn"
        >
          <IconZoomIn :size="16" />
        </button>
        <button
          type="button"
          class="dc-icon-button"
          data-testid="document-converter-preview-fit"
          aria-label="Anpassa till vyn"
          title="Anpassa till vyn"
          @click="zoom.fitToView"
        >
          <IconFitView :size="16" />
        </button>
      </div>
    </header>

    <div class="dc-preview-body">
      <section
        class="dc-artifact-result"
        aria-label="Resultat"
      >
        <div
          v-if="activePreviewUrl"
          ref="previewViewport"
          class="dc-pdf-viewport"
          data-testid="document-converter-pdf-viewport"
        >
          <div
            class="dc-pdf-stage"
            data-testid="document-converter-pdf-stage"
            :class="{ 'dc-pdf-stage--contained': zoom.fitsViewport.value }"
          >
            <div
              class="dc-pdf-surface"
              data-testid="document-converter-pdf-surface"
              :style="zoom.scaledSurfaceStyle.value"
            >
              <iframe
                data-testid="document-converter-pdf-frame"
                class="dc-artifact-frame"
                :src="activePreviewUrl"
                :title="resultTitle"
              />
            </div>
          </div>
        </div>
        <div
          v-else
          class="dc-result-empty"
        >
          <strong>{{ resultStateLabel }}</strong>
        </div>
      </section>
    </div>
  </section>
</template>
