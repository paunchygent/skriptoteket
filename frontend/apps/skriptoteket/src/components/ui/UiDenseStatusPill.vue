<script setup lang="ts">
/**
 * Shared dense status pill for compact planner/editor workspace statuses.
 *
 * Relationships:
 * - passive counterpart to the dense action primitives in PR-0157
 * - used for compact CRUD/workspace states such as unsaved, lock, and similar toolbar badges
 */

import { computed } from "vue";

import { denseStatusPillClass, type DenseStatusTone } from "./denseToolPrimitives";

const props = withDefaults(
  defineProps<{
    label: string;
    tone?: DenseStatusTone;
    title?: string;
  }>(),
  {
    tone: "neutral",
    title: undefined,
  },
);

const pillClass = computed(() =>
  denseStatusPillClass({
    tone: props.tone,
  }),
);
</script>

<template>
  <span
    :class="pillClass"
    :title="title"
    data-ui="dense-status-pill"
  >
    {{ label }}
  </span>
</template>
