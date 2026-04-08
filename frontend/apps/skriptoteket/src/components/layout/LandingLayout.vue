<script setup lang="ts">
/**
 * Signed-out landing shell.
 *
 * This layout frames public-entry routes that share the unauthenticated
 * Skriptoteket shell, keeping header actions quiet so route-level hero
 * surfaces can own the strongest next step while all auth entry flows route
 * through the dedicated `/auth/login` page.
 */

import BrandLogo from "../brand/BrandLogo.vue";
import HelpButton from "../help/HelpButton.vue";
import { buildLandingAuthEntryLocation } from "../../composables/auth/authEntryNavigation";
import { useRoute, useRouter } from "vue-router";

const publicClassroomPlannerPath = "/public/apps/classroom.group-seating-studio";
const route = useRoute();
const router = useRouter();

async function goToAuthEntry(): Promise<void> {
  await router.push(buildLandingAuthEntryLocation(route));
}
</script>

<template>
  <div class="landing-shell">
    <header class="landing-header">
      <div class="landing-header-inner">
        <div class="landing-header-leading">
          <RouterLink
            to="/"
            class="landing-brand"
          >
            <BrandLogo height="28px" />
          </RouterLink>

          <nav
            class="landing-nav"
            aria-label="Publika genvägar"
          >
            <RouterLink
              :to="publicClassroomPlannerPath"
              class="landing-nav-link"
            >
              Klassrumskartan
            </RouterLink>
          </nav>
        </div>

        <div class="landing-header-actions">
          <button
            type="button"
            class="landing-header-link"
            @click="void goToAuthEntry()"
          >
            Logga in
          </button>
          <HelpButton />
        </div>
      </div>
    </header>

    <main class="landing-main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.landing-shell {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}

.landing-header {
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
}

.landing-header-inner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--huleedu-space-3) var(--huleedu-space-6);
  width: 100%;
  max-width: var(--huleedu-max-width-6xl);
  margin: 0 auto;
  padding: var(--huleedu-space-4) var(--huleedu-space-6);
}

.landing-header-leading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--huleedu-space-3) var(--huleedu-space-6);
}

.landing-brand {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  text-decoration: none;
  user-select: none;
}

.landing-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--huleedu-space-4);
}

.landing-nav-link,
.landing-header-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  color: var(--huleedu-navy);
  font-size: var(--huleedu-text-sm);
  font-weight: var(--huleedu-font-semibold);
  line-height: 1.3;
  text-decoration: none;
  transition:
    color var(--huleedu-duration-default) var(--huleedu-ease-default),
    opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.landing-nav-link::after,
.landing-header-link::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0.1rem;
  height: 1px;
  background-color: currentcolor;
  opacity: 0;
  transform: scaleX(0.55);
  transform-origin: left center;
  transition:
    opacity var(--huleedu-duration-default) var(--huleedu-ease-default),
    transform var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.landing-header-link {
  color: var(--huleedu-navy-70);
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}

.landing-header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--huleedu-space-3);
}

.landing-brand:hover,
.landing-nav-link:hover,
.landing-header-link:hover {
  color: var(--huleedu-burgundy);
}

.landing-nav-link:hover::after,
.landing-nav-link:focus-visible::after,
.landing-header-link:hover::after,
.landing-header-link:focus-visible::after {
  opacity: 1;
  transform: scaleX(1);
}

.landing-nav-link:focus-visible,
.landing-header-link:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--huleedu-burgundy) 40%, transparent);
  outline-offset: 4px;
}

.landing-main {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  max-width: var(--huleedu-max-width-6xl);
  margin: 0 auto;
  padding: var(--huleedu-space-8) var(--huleedu-space-6);
  width: 100%;
}

@media (max-width: 48rem) {
  .landing-header-inner,
  .landing-main {
    padding-inline: var(--huleedu-space-4);
  }

  .landing-header-actions {
    gap: var(--huleedu-space-2) var(--huleedu-space-3);
  }
}
</style>
