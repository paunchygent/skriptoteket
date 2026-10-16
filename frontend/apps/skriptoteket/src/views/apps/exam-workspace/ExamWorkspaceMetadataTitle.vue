<script setup lang="ts">
/** Toolbar trigger for the document metadata drawer. */
defineProps<{ title: string; isOpen: boolean; drawerId: string }>();
const emit = defineEmits<{ open: [] }>();
</script>

<template>
  <button
    type="button"
    class="min-w-0 truncate text-sm font-medium leading-snug text-navy underline decoration-navy/35 underline-offset-4"
    :title="title"
    aria-haspopup="dialog"
    :aria-expanded="isOpen"
    :aria-controls="drawerId"
    data-test="exam-workspace-summary-title"
    @click="emit('open')"
  >
    {{ title }}
  </button>
</template>
