<script setup lang="ts">
/**
 * Graduation-cap icon wrapper.
 *
 * This module exposes the teacher/education affordance through the shared
 * icon registry for rules that refer to the teacher's position.
 */

import { GraduationCap } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <GraduationCap
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
