<script setup lang="ts">
/**
 * Purpose:
 *     Render the shared dense-control loading spinner.
 *
 * Relationships:
 *     - Rendered by UiDenseActionButton for in-place busy feedback.
 *     - LoaderCircle comes from the `@lucide/vue` 1.47.0 peer dependency.
 *     - Decorative by default; pass `label` only when the spinner itself is
 *       the accessible content.
 */

import { LoaderCircle } from "@lucide/vue";

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
    :stroke-width="2.4"
    :aria-hidden="label ? undefined : 'true'"
    :aria-label="label"
    data-ui="dense-spinner"
  />
</template>
