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
  }>(),
  {
    tone: "neutral",
    interactive: false,
    active: false,
  },
);

const pillClass = computed(() =>
  denseStatusPillClass({
    tone: props.tone,
    interactive: props.interactive,
    active: props.active,
  }),
);
</script>

<template>
  <span
    :class="pillClass"
    data-ui="dense-status-pill"
  >
    {{ label }}
  </span>
</template>
