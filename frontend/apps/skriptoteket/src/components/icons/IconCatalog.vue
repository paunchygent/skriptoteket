<script setup lang="ts">
/**
 * Canonical catalog/library symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - available for shared site catalog/navigation semantics
 */

import { Library } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Library
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
