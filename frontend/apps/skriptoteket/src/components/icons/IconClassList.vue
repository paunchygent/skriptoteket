<script setup lang="ts">
/**
 * Canonical class-list symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - reserves clipboard/list semantics for class-list surfaces
 */

import { ClipboardList } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <ClipboardList
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
