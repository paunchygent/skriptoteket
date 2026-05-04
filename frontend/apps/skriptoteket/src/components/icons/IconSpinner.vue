<script setup lang="ts">
/**
 * Canonical loading/spinner symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by dense loading primitives rather than importing Lucide directly
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
  />
</template>
