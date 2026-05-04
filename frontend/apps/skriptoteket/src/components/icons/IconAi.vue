<script setup lang="ts">
/**
 * Canonical AI-assist symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - available for AI-supported generation and assistive actions
 */

import { Sparkles } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Sparkles
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
