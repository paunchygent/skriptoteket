<script setup lang="ts">
/**
 * Canonical lock symbol for fixed assignments and protected states.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - used by dense planner controls where text would be too slow to scan
 */

import { LockKeyhole } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <LockKeyhole
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
