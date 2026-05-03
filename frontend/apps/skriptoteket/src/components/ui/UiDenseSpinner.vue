<script setup lang="ts">
/**
 * Shared dense-control spinner.
 *
 * Relationships:
 * - used by dense buttons and split buttons for in-place processing feedback
 * - keeps planner/editor loading affordances in the shared primitive layer
 */

import { LoaderCircle } from "lucide-vue-next";

withDefaults(
  defineProps<{
    size?: number;
    label?: string;
  }>(),
  {
    size: 12,
    label: undefined,
  },
);
</script>

<template>
  <LoaderCircle
    class="animate-spin"
    :size="size"
    :aria-hidden="label ? undefined : 'true'"
    :aria-label="label"
    :stroke-width="2.4"
    data-ui="dense-spinner"
  />
</template>
