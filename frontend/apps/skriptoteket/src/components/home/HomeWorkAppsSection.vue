<script setup lang="ts">
/**
 * Primary authenticated home app shelf.
 *
 * Relationships:
 * - renders the approved app-first lane model from `homeWorkApps.ts`
 * - keeps truthful runtime links and non-linkable lanes visually aligned on
 *   the signed-in home surface
 */

import type { HomeWorkApp } from "./homeWorkApps";

defineProps<{
  apps: readonly HomeWorkApp[];
}>();
</script>

<template>
  <section
    data-testid="home-work-apps"
    class="space-y-4"
  >
    <div class="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
      <component
        :is="app.to ? 'RouterLink' : 'article'"
        v-for="app in apps"
        :key="app.id"
        v-bind="app.to ? { to: app.to } : { 'aria-disabled': 'true' }"
        :data-testid="`home-work-app-${app.id}`"
        :data-app-linkable="app.to ? 'true' : 'false'"
        class="home-work-app"
        :class="app.to ? 'group no-underline' : 'home-work-app--static'"
      >
        <div
          class="home-work-app__graphic"
          aria-hidden="true"
        >
          <img
            :src="app.imageSrc"
            alt=""
            class="home-work-app__image"
            loading="lazy"
            decoding="async"
          >
        </div>

        <div class="home-work-app__body">
          <div class="space-y-2">
            <h3 class="text-xl font-semibold text-navy">
              {{ app.title }}
            </h3>
            <p class="text-sm leading-6 text-navy/70">
              {{ app.description }}
            </p>
          </div>

          <p
            v-if="app.availabilityLabel"
            class="text-xs font-semibold"
            :class="app.to ? 'text-action' : 'text-navy/55'"
          >
            {{ app.availabilityLabel }}
          </p>
        </div>
      </component>
    </div>
  </section>
</template>

<style scoped>
.home-work-app {
  display: grid;
  grid-template-rows: 9rem minmax(0, 1fr);
  min-height: 18rem;
  border: 1px solid var(--color-navy);
  background: var(--color-panel);
}

.home-work-app__body {
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 1rem;
  padding: 1rem;
}

.home-work-app__graphic {
  position: relative;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-bottom: 1px solid color-mix(in srgb, var(--color-navy) 18%, transparent);
  background: color-mix(in srgb, var(--color-canvas) 88%, var(--color-panel));
}

.home-work-app__image {
  width: min(7.25rem, 56%);
  aspect-ratio: 1;
  object-fit: contain;
}

.group:hover .home-work-app__graphic,
.group:focus-visible .home-work-app__graphic {
  background-color: var(--color-paper);
}

.group:hover .home-work-app__body h3,
.group:focus-visible .home-work-app__body h3 {
  color: var(--color-action);
}

.home-work-app--static {
  background: color-mix(in srgb, var(--color-panel) 88%, var(--color-canvas));
}
</style>
