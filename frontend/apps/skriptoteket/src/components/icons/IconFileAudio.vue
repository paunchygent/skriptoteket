<script setup lang="ts">
/**
 * Canonical audio-file symbol.
 *
 * Relationships:
 * - exported through `src/components/icons/index.ts`
 * - consumed by audio/video upload and transcript conversion surfaces
 */

import { FileAudio } from "lucide-vue-next";

defineProps<{
  size?: number;
}>();
</script>

<template>
  <FileAudio
    :size="size ?? 24"
    :stroke-width="2.25"
    aria-hidden="true"
  />
</template>
