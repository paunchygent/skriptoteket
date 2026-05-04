<script setup lang="ts">
/**
 * Canonical zoom-in symbol for dense canvas controls.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by planner/editor viewport and canvas primitives
 */

import { ZoomIn } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ZoomIn
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
