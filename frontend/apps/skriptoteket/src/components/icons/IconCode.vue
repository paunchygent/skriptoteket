<script setup lang="ts">
/**
 * Canonical code/editor symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - available for code and editor mode affordances
 */

import { Code } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Code
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
