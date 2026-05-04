<script setup lang="ts">
/**
 * Canonical zoom-out symbol for dense canvas controls.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by planner/editor viewport and canvas primitives
 */

import { ZoomOut } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ZoomOut
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
