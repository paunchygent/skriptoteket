<script setup lang="ts">
/**
 * Canonical fit-view symbol for canvas scaling controls.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by room/canvas viewport controls and shared dense menus
 */

import { Fullscreen } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Fullscreen
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
