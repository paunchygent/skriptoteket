<script setup lang="ts">
/**
 * Canonical classroom symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - uses the approved Tabler fallback for teacher/classroom semantics
 */

import { IconChalkboardTeacher } from "@tabler/icons-vue";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <IconChalkboardTeacher
    :size="size ?? 24"
    stroke-width="2"
    aria-hidden="true"
  />
</template>
