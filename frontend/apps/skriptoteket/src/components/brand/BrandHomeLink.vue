<script setup lang="ts">
/**
 * The shared Skriptoteket home link around the wordmark.
 *
 * Relationships:
 * - `AuthTopBar` and `LandingLayout` both place this link at the left of their
 *   56 px bar, so the signed-in and signed-out bars show one brand mark at one
 *   height (TASK-SKRIPT-REP-0061)
 * - `BrandLogo` draws the artwork and owns the wordmark tokens; this component
 *   owns the home target, the touch height and the focus ring
 * - the default slot carries the bar's app label, such as the exam workspace
 *   name in `AuthTopBar`
 */

import { RouterLink } from "vue-router";

import BrandLogo from "./BrandLogo.vue";
</script>

<template>
  <RouterLink
    to="/"
    class="brand-home-link"
  >
    <BrandLogo height="var(--huleedu-space-10)" />
    <slot />
  </RouterLink>
</template>

<style scoped>
.brand-home-link {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: var(--huleedu-space-1-5);
  min-height: var(--huleedu-action-control-height);
  white-space: nowrap;
  text-decoration: none;
}

.brand-home-link:focus-visible {
  outline: var(--huleedu-border-width-2) solid var(--huleedu-action-40);
  outline-offset: var(--huleedu-space-0-5);
  border-radius: var(--huleedu-radius-md);
}
</style>
