<script setup lang="ts">
/**
 * Signed-out landing preview for Klassrumskartan.
 *
 * This component owns the decorative classroom SVG used in the public-entry
 * hero so the landing route can keep layout and copy separate from the
 * preview-asset delivery path.
 */

import heroPreviewUrl from "../../assets/home/klassrumskartan/landing/redesign-v5/hero-preview.svg?no-inline";
</script>

<template>
  <aside class="hero-preview">
    <img
      :src="heroPreviewUrl"
      alt="Klassrum med tavla, dörr och placerade elever"
      width="320"
      height="220"
      class="block h-auto w-full"
    >
  </aside>
</template>

<style scoped>
.hero-preview {
  border: 2px solid var(--color-navy);
  background-color: var(--color-canvas);
  box-shadow: 4px 4px 0 0 var(--color-navy);
  padding: 1.125rem;
}
</style>
