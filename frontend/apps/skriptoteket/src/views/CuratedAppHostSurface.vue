<script setup lang="ts">
/**
 * Shared curated-app host surface.
 *
 * This presentational component renders the common loading, error, and
 * bespoke-view fallback states used by both authenticated and public curated
 * app host routes.
 */

import type { Component } from "vue";

import { SystemMessage, UiDenseSpinner } from "../components/ui/shared";

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
    <SystemMessage v-if="isLoading">
      <span class="inline-flex items-center gap-2">
        <UiDenseSpinner />
        Laddar...
      </span>
    </SystemMessage>

    <SystemMessage
      v-else-if="errorMessage"
      tone="failure"
    >
      {{ errorMessage }}
    </SystemMessage>

    <SystemMessage
      v-else
      tone="warning"
    >
      <div class="space-y-2">
        <p class="text-sm font-semibold">
          Den här appen kräver en anpassad vy som inte är installerad ännu.
        </p>
        <p class="text-sm text-navy/70">
          Kontakta admin eller uppdatera installationen för att få tillgång till appen.
        </p>
      </div>
    </SystemMessage>
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
