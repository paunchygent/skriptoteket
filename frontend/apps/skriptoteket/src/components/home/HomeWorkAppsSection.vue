<script setup lang="ts">
/**
 * Primary authenticated home app shelf.
 *
 * Relationships:
 * - renders the approved app-first lane model from `homeWorkApps.ts`
 * - keeps truthful runtime links and non-linkable lanes visually aligned on
 *   the signed-in home surface
 */

import type { HomeWorkApp, HomeWorkAppGraphic } from "./homeWorkApps";

defineProps<{
  apps: readonly HomeWorkApp[];
}>();

function graphicMarkCount(graphic: HomeWorkAppGraphic): number {
  switch (graphic) {
    case "classroom":
      return 5;
    case "exam":
      return 4;
    case "audio":
      return 9;
    case "document":
      return 3;
    case "code":
      return 4;
  }
}
</script>

<template>
  <section
    data-testid="home-work-apps"
    class="space-y-4"
  >
    <div class="max-w-[40rem] space-y-2">
      <h2 class="font-serif text-3xl font-semibold text-navy md:text-[2.35rem]">
        Arbetsappar
      </h2>
      <p class="text-sm leading-6 text-navy/70 md:text-base">
        Välj den arbetsyta som matchar nästa steg i ditt arbete.
      </p>
    </div>

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
          :class="`home-work-app__graphic--${app.graphic}`"
          aria-hidden="true"
        >
          <span
            v-for="markIndex in graphicMarkCount(app.graphic)"
            :key="markIndex"
            class="home-work-app__graphic-mark"
          />
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
  grid-template-rows: 7.5rem minmax(0, 1fr);
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
  overflow: hidden;
  border-bottom: 1px solid color-mix(in srgb, var(--color-navy) 18%, transparent);
  background:
    linear-gradient(var(--color-navy) 1px, transparent 1px),
    linear-gradient(90deg, var(--color-navy) 1px, transparent 1px),
    var(--color-canvas);
  background-size: var(--huleedu-grid-size) var(--huleedu-grid-size);
  opacity: 1;
}

.home-work-app__graphic::after {
  content: "";
  position: absolute;
  inset: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--color-navy) 18%, transparent);
}

.home-work-app__graphic-mark {
  position: absolute;
  border: 1px solid var(--color-navy);
  background: var(--color-paper);
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

.home-work-app--static .home-work-app__graphic-mark:nth-child(3) {
  background: var(--color-critical);
}

.home-work-app__graphic--classroom .home-work-app__graphic-mark:nth-child(1) {
  left: 1.5rem;
  top: 1.5rem;
  width: 2rem;
  height: 1.2rem;
}

.home-work-app__graphic--classroom .home-work-app__graphic-mark:nth-child(2) {
  left: 4.15rem;
  top: 1.5rem;
  width: 2rem;
  height: 1.2rem;
}

.home-work-app__graphic--classroom .home-work-app__graphic-mark:nth-child(3) {
  left: 6.8rem;
  top: 1.5rem;
  width: 2rem;
  height: 1.2rem;
}

.home-work-app__graphic--classroom .home-work-app__graphic-mark:nth-child(4) {
  left: 2.6rem;
  top: 4rem;
  width: 2rem;
  height: 1.2rem;
}

.home-work-app__graphic--classroom .home-work-app__graphic-mark:nth-child(5) {
  left: 5.25rem;
  top: 4rem;
  width: 2rem;
  height: 1.2rem;
}

.home-work-app__graphic--exam .home-work-app__graphic-mark:nth-child(1) {
  left: 1.8rem;
  top: 1.25rem;
  width: 6rem;
  height: 3.9rem;
  background: var(--color-canvas);
}

.home-work-app__graphic--exam .home-work-app__graphic-mark:nth-child(2) {
  left: 2.6rem;
  top: 2.2rem;
  width: 3.75rem;
  height: 0.25rem;
  border-width: 0;
  background: var(--color-navy);
}

.home-work-app__graphic--exam .home-work-app__graphic-mark:nth-child(3) {
  left: 2.6rem;
  top: 3.15rem;
  width: 4.5rem;
  height: 0.25rem;
  border-width: 0;
  background: var(--color-navy);
}

.home-work-app__graphic--exam .home-work-app__graphic-mark:nth-child(4) {
  left: 2.6rem;
  top: 4.1rem;
  width: 3rem;
  height: 0.25rem;
  border-width: 0;
  background: var(--color-navy);
}

.home-work-app__graphic--audio .home-work-app__graphic-mark {
  bottom: 1.25rem;
  width: 0.55rem;
  border-width: 0;
  background: var(--color-navy);
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(1) {
  left: 1.5rem;
  height: 1.25rem;
  opacity: 0.35;
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(2) {
  left: 2.4rem;
  height: 2.9rem;
  opacity: 0.72;
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(3) {
  left: 3.3rem;
  height: 1.9rem;
  opacity: 0.52;
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(4) {
  left: 4.2rem;
  height: 4rem;
  opacity: 0.88;
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(5) {
  left: 5.1rem;
  height: 5rem;
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(6) {
  left: 6rem;
  height: 3.7rem;
  opacity: 0.8;
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(7) {
  left: 6.9rem;
  height: 2.3rem;
  opacity: 0.58;
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(8) {
  left: 7.8rem;
  height: 3.2rem;
  opacity: 0.7;
}

.home-work-app__graphic--audio .home-work-app__graphic-mark:nth-child(9) {
  left: 8.7rem;
  height: 1.5rem;
  opacity: 0.4;
}

.home-work-app__graphic--document .home-work-app__graphic-mark:nth-child(1) {
  left: 1.8rem;
  top: 1.75rem;
  width: 3.35rem;
  height: 2.65rem;
}

.home-work-app__graphic--document .home-work-app__graphic-mark:nth-child(2) {
  left: 4rem;
  top: 1.15rem;
  width: 3.35rem;
  height: 3.2rem;
  background: var(--color-canvas);
}

.home-work-app__graphic--document .home-work-app__graphic-mark:nth-child(3) {
  left: 3rem;
  top: 3.2rem;
  width: 4.5rem;
  height: 0.9rem;
  border-width: 1px 0;
}

.home-work-app__graphic--code {
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--color-navy) 12%, transparent) 0 2.1rem, transparent 2.1rem),
    var(--color-paper);
}

.home-work-app__graphic--code .home-work-app__graphic-mark {
  left: 3rem;
  height: 0.3rem;
  border-width: 0;
  background: var(--color-navy);
}

.home-work-app__graphic--code .home-work-app__graphic-mark:nth-child(1) {
  top: 1.65rem;
  width: 4.35rem;
  opacity: 0.72;
}

.home-work-app__graphic--code .home-work-app__graphic-mark:nth-child(2) {
  top: 2.75rem;
  width: 6rem;
  opacity: 0.52;
}

.home-work-app__graphic--code .home-work-app__graphic-mark:nth-child(3) {
  top: 3.85rem;
  width: 5rem;
  opacity: 0.65;
}

.home-work-app__graphic--code .home-work-app__graphic-mark:nth-child(4) {
  left: 8.25rem;
  top: 3.5rem;
  width: 0.35rem;
  height: 1rem;
  background: var(--color-critical);
}
</style>
