<script setup lang="ts">
/**
 * Placeholder notice for a question whose conversion batch is still running.
 * The item shows its source text and cannot be changed until its batch
 * replaces it.
 */
</script>

<template>
  <p
    class="border-b border-navy bg-saffron px-4 py-2 text-xs font-semibold leading-snug"
    role="note"
    data-test="exam-workspace-converting-notice"
  >
    Frågan konverteras fortfarande. Källtexten visas tills den är klar och går inte att ändra
    under tiden.
  </p>
</template>
