<script setup lang="ts">
/**
 * Canonical debug symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - available for debug and diagnostics actions
 */

import { Bug } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Bug
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
