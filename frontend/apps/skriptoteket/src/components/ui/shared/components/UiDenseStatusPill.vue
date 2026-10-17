<script setup lang="ts">
/**
 * Purpose:
 *     Render a compact status pill using shared dense status tone classes.
 *
 * Relationships:
 *     - Uses denseStatusPillClass from the primitive contract.
 *     - Keeps status chips visually aligned across integrated repos.
 */

import { computed } from "vue";

import { denseStatusPillClass, type DenseStatusTone } from "../denseToolPrimitives";

const props = withDefaults(
  defineProps<{
    label: string;
    tone?: DenseStatusTone;
    interactive?: boolean;
    active?: boolean;
    compact?: boolean;
  }>(),
  {
    tone: "neutral",
    interactive: false,
    active: false,
    compact: false,
  },
);

const pillClass = computed(() =>
  denseStatusPillClass({
    tone: props.tone,
    interactive: props.interactive,
    active: props.active,
    compact: props.compact,
  }),
);
</script>

<template>
  <span
    v-if="compact"
    :class="pillClass"
    data-ui="dense-status-pill"
  >
    <span
      class="h-2 w-2 shrink-0 rounded-full bg-current"
      aria-hidden="true"
    ></span>
    <span class="sr-only">{{ label }}</span>
  </span>
  <span
    v-else
    :class="pillClass"
    data-ui="dense-status-pill"
  >
    {{ label }}
  </span>
</template>
