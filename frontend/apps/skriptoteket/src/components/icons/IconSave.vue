<script setup lang="ts">
/**
 * Save action icon wrapper.
 *
 * Relationships:
 * - exposes the shared save symbol for compact planner and editor actions
 * - keeps Lucide implementation details behind the app icon registry
 */

import { Save } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <Save
    :size="size ?? 24"
    :stroke-width="2.5"
    aria-hidden="true"
  />
</template>
