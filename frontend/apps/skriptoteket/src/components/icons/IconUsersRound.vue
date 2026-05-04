<script setup lang="ts">
/**
 * Users-round icon wrapper.
 *
 * This module exposes the canonical students/groups affordance through the
 * shared icon registry for planner student lists and group mode navigation.
 */

import { UsersRound } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <UsersRound
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
