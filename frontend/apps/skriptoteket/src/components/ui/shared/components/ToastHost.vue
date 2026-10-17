<script setup lang="ts">
/**
 * Purpose:
 *     Render shared toast notifications from consumer-owned toast state.
 *
 * Relationships:
 *     - Avoids coupling the resource package to any app-specific Pinia store.
 *     - Uses the same token tone vocabulary as SystemMessage.
 *     - Shows each variant's status glyph through UiGlyph (`info`,
 *       `status-success`, `status-warning`, `status-failure`).
 *
 * Contract:
 *     - Order: consumers pass the newest toast first. With the default
 *       `placement="top"` the toasts render in array order, top to bottom, so
 *       the newest sits on top. With `placement="bottom"` the stack is
 *       anchored at its bottom edge and grows upward: the newest toast sits
 *       nearest the bottom edge. Consumers keep at most three toasts.
 *     - Live regions: warning and failure toasts are `role="alert"`; info and
 *       success toasts are `role="status"`. The host itself is not a live
 *       region, so live regions never nest.
 *     - Placement: the package has no placement tokens, so the consumer sets
 *       `--huleedu-toast-top` (top placement) or `--huleedu-toast-bottom`
 *       (bottom placement), `--huleedu-toast-inline-end` and
 *       `--huleedu-toast-width` on the host or an ancestor. Without them the
 *       stack sits at the top right, or the bottom right, with the page gutter.
 *       The host is fixed, so showing or dismissing a toast moves nothing on
 *       the page.
 *     - Surface: frosted (translucent content surface over a backdrop blur,
 *       an inner light edge, the small shadow and the variant border).
 *     - Glyph colour: info, success and warning glyphs use the solid
 *       `-strong` shades so they reach 3:1 over any frosted backdrop; the
 *       failure glyph and all text keep their base colours.
 *     - `closeLabel` names every close control; the default is Swedish.
 */

import { computed } from "vue";

import type { UiGlyphMeaning } from "../uiGlyphs";
import UiGlyph from "./UiGlyph.vue";

export type ToastVariant = "info" | "success" | "warning" | "failure";
export type ToastPlacement = "top" | "bottom";
export type ToastItem = {
  id: string;
  message: string;
  variant?: ToastVariant;
};

const props = withDefaults(
  defineProps<{
    toasts?: ToastItem[];
    closeLabel?: string;
    placement?: ToastPlacement;
  }>(),
  {
    toasts: () => [],
    closeLabel: "Stäng avisering",
    placement: "top",
  },
);

defineEmits<{ dismiss: [id: string] }>();

const STATUS_GLYPHS: Record<ToastVariant, UiGlyphMeaning> = {
  info: "info",
  success: "status-success",
  warning: "status-warning",
  failure: "status-failure",
};

const items = computed(() =>
  props.toasts.map((toast) => {
    const variant = toast.variant ?? "info";
    return {
      ...toast,
      variant,
      glyph: STATUS_GLYPHS[variant],
      role: variant === "warning" || variant === "failure" ? "alert" : "status",
    };
  }),
);
</script>

<template>
  <div
    class="huleedu-toast-host"
    :class="`huleedu-toast-host--${placement}`"
    data-ui="toast-host"
    :data-placement="placement"
  >
    <article
      v-for="toast in items"
      :key="toast.id"
      class="huleedu-toast"
      :class="`huleedu-toast--${toast.variant}`"
      :data-variant="toast.variant"
      :role="toast.role"
    >
      <span class="huleedu-toast-glyph">
        <UiGlyph :meaning="toast.glyph" />
      </span>
      <p class="huleedu-toast-message">{{ toast.message }}</p>
      <button
        type="button"
        class="huleedu-toast-close"
        :aria-label="closeLabel"
        @click="$emit('dismiss', toast.id)"
      >
        <UiGlyph meaning="close" />
      </button>
    </article>
  </div>
</template>

<style scoped>
.huleedu-toast-host {
  position: fixed;
  top: var(--huleedu-toast-top, var(--huleedu-space-4));
  right: var(--huleedu-toast-inline-end, var(--huleedu-space-4));
  z-index: var(--huleedu-z-tooltip);
  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-2);
  width: var(--huleedu-toast-width, min(24rem, calc(100vw - 2 * var(--huleedu-space-4))));
  pointer-events: none;
}

/* Bottom placement: the stack's bottom edge is fixed and it grows upward; the
   first (newest) toast sits nearest the bottom edge. */
.huleedu-toast-host--bottom {
  top: auto;
  bottom: var(--huleedu-toast-bottom, var(--huleedu-space-4));
  flex-direction: column-reverse;
}

.huleedu-toast {
  --huleedu-toast-tone-border: var(--huleedu-workbench-control-border);
  --huleedu-toast-tone-text: var(--huleedu-navy);
  --huleedu-toast-tone-glyph: var(--huleedu-action-strong);
  /* Frosted surface: opacity, blur, saturation and inner-edge opacity. */
  --huleedu-toast-frosted-opacity: 50%;
  --huleedu-toast-frosted-blur: 12px;
  --huleedu-toast-frosted-saturate: 180%;
  --huleedu-toast-frosted-edge-opacity: 70%;
  --huleedu-toast-line: calc(var(--huleedu-type-supporting-size) * var(--huleedu-type-body-leading));

  display: grid;
  grid-template-columns: var(--huleedu-navigation-icon-size) minmax(0, 1fr) var(--huleedu-action-control-height);
  column-gap: var(--huleedu-space-2);
  align-items: start;
  min-width: 0;
  padding-inline-start: var(--huleedu-space-3);
  border: var(--huleedu-border-width) solid var(--huleedu-toast-tone-border);
  border-radius: var(--huleedu-panel-radius);
  background: color-mix(in srgb, var(--huleedu-surface-content) var(--huleedu-toast-frosted-opacity), transparent);
  -webkit-backdrop-filter: blur(var(--huleedu-toast-frosted-blur)) saturate(var(--huleedu-toast-frosted-saturate));
  backdrop-filter: blur(var(--huleedu-toast-frosted-blur)) saturate(var(--huleedu-toast-frosted-saturate));
  box-shadow:
    inset 0 0 0 var(--huleedu-border-width) color-mix(in srgb, var(--huleedu-surface-content) var(--huleedu-toast-frosted-edge-opacity), transparent),
    var(--huleedu-shadow-sm);
  color: var(--huleedu-toast-tone-text);
  font: var(--huleedu-type-supporting-weight) var(--huleedu-type-supporting-size) / var(--huleedu-type-body-leading) var(--huleedu-font-interface);
  pointer-events: auto;
}

.huleedu-toast--success {
  --huleedu-toast-tone-border: var(--huleedu-success-45);
  --huleedu-toast-tone-glyph: var(--huleedu-success-strong);
}

.huleedu-toast--warning {
  --huleedu-toast-tone-border: var(--huleedu-warning-50);
  --huleedu-toast-tone-glyph: var(--huleedu-warning-strong);
}

.huleedu-toast--failure {
  --huleedu-toast-tone-border: var(--huleedu-critical-30);
  --huleedu-toast-tone-text: var(--huleedu-critical);
  --huleedu-toast-tone-glyph: var(--huleedu-critical);
}

/* The glyph centres on the first text line: text inset + half the line/glyph difference. */
.huleedu-toast-glyph {
  display: block;
  width: var(--huleedu-navigation-icon-size);
  height: var(--huleedu-navigation-icon-size);
  margin-block-start: calc(var(--huleedu-space-3) + (var(--huleedu-toast-line) - var(--huleedu-navigation-icon-size)) / 2);
  color: var(--huleedu-toast-tone-glyph);
}

.huleedu-toast-glyph :deep(svg),
.huleedu-toast-close :deep(svg) {
  width: var(--huleedu-navigation-icon-size);
  height: var(--huleedu-navigation-icon-size);
}

.huleedu-toast-message {
  margin: 0;
  padding-block: var(--huleedu-space-3);
  overflow-wrap: anywhere;
}

/* 44px touch target on every band; the message's first line centres on it. */
.huleedu-toast-close {
  display: inline-grid;
  place-items: center;
  width: var(--huleedu-action-control-height);
  height: var(--huleedu-action-control-height);
  padding: 0;
  border: 0;
  border-radius: var(--huleedu-workbench-control-radius);
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.huleedu-toast-close:hover {
  background: var(--huleedu-navy-05);
}

.huleedu-toast-close:focus-visible {
  outline: var(--huleedu-border-width-2) solid var(--huleedu-action);
  outline-offset: calc(var(--huleedu-border-width-2) * -1);
}
</style>
