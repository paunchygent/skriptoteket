<script setup lang="ts">
/**
 * Placeholder notice for a question whose conversion batch is still running.
 * The item shows its source text until the batch fills it; a teacher edit
 * keeps the teacher's version and the late conversion result is dropped.
 */
</script>

<template>
  <p
    class="border-b border-navy bg-saffron px-4 py-2 text-xs font-semibold leading-snug"
    role="note"
    data-test="exam-workspace-converting-notice"
  >
    Frågan konverteras fortfarande. Källtexten visas tills den är klar. Ändrar du frågan
    behålls din version och konverteringens resultat används inte.
  </p>
</template>
