<script setup lang="ts">
/**
 * Shared curated-app host surface.
 *
 * This presentational component renders the common loading, error, and
 * bespoke-view fallback states used by both authenticated and public curated
 * app host routes.
 */

import type { Component } from "vue";

defineProps<{
  errorMessage: string | null;
  fallbackView: Component | null;
  fallbackViewProps: Record<string, unknown>;
  hostView: Component | null;
  hostViewProps: Record<string, unknown>;
  isLoading: boolean;
  shouldBlock: boolean;
}>();
</script>

<template>
  <div
    v-if="isLoading || errorMessage || shouldBlock"
    class="max-w-3xl space-y-6"
  >
    <div
      v-if="isLoading"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-navy/70 text-sm"
    >
      Laddar...
    </div>

    <div
      v-else-if="errorMessage"
      class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
    >
      {{ errorMessage }}
    </div>

    <div
      v-else
      class="p-4 border border-burgundy bg-white shadow-brutal-sm space-y-2"
    >
      <p class="text-sm font-semibold text-burgundy">
        Den här appen kräver en anpassad vy som inte är installerad ännu.
      </p>
      <p class="text-sm text-navy/70">
        Kontakta admin eller uppdatera installationen för att få tillgång till appen.
      </p>
    </div>
  </div>

  <component
    :is="hostView"
    v-else-if="hostView"
    v-bind="hostViewProps"
  />

  <component
    :is="fallbackView"
    v-else-if="fallbackView"
    v-bind="fallbackViewProps"
  />
</template>
