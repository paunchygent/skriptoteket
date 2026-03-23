<script setup lang="ts">
/**
 * Compact icon-first toolbar button for planner action rows.
 *
 * This keeps recurring secondary actions short enough to coexist with
 * selectors and primary buttons in the same control bar without adding another
 * line of chrome.
 */

import { useAttrs } from "vue";

defineOptions({
  inheritAttrs: false,
});

defineProps<{
  label: string;
  title?: string;
  disabled?: boolean;
}>();

const attrs = useAttrs();
</script>

<template>
  <button
    type="button"
    v-bind="attrs"
    :aria-label="label"
    :title="title ?? label"
    :disabled="disabled"
    class="grid h-9 w-9 place-items-center rounded-sm bg-transparent text-navy transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-burgundy/40 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:text-navy/25 hover:bg-canvas/60"
  >
    <slot />
  </button>
</template>
