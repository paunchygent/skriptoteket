<script setup lang="ts">
/**
 * Shared dense-control spinner.
 *
 * Relationships:
 * - used by dense buttons and split buttons for in-place processing feedback
 * - keeps planner/editor loading affordances in the shared primitive layer
 */

import { IconSpinner } from "../icons";

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
  <IconSpinner
    class="animate-spin"
    :size="size"
    :label="label"
    data-ui="dense-spinner"
  />
</template>
