<script setup lang="ts">
/**
 * Canonical owned-files/vault symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - available for file/library surfaces outside export-download actions
 */

import { FolderOpen } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <FolderOpen
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
