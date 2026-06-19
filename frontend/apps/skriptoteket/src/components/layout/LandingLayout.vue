<script setup lang="ts">
/**
 * Signed-out landing shell.
 *
 * This layout frames public-entry routes that share the unauthenticated
 * Skriptoteket shell, keeping header actions quiet so route-level hero
 * surfaces can own the strongest next step while login/help stay on one quiet
 * header row and login affordances open the HuleEdu ceremony directly.
 */

import { computed } from "vue";
import { useRoute } from "vue-router";

import BrandLogo from "../brand/BrandLogo.vue";
import HelpButton from "../help/HelpButton.vue";
import { sharedAuthCeremonyUrl } from "../../api/sharedAuth";
import { resolveLandingAuthContinuation } from "../../composables/auth/authEntryNavigation";

const route = useRoute();
const loginUrl = computed(() => {
  const continuation = resolveLandingAuthContinuation(route);
  return sharedAuthCeremonyUrl({
    nextPath: continuation.nextPath,
    origin: window.location.origin,
  });
});
</script>

<template>
  <div class="landing-shell">
    <header class="landing-header">
      <div class="landing-header-inner">
        <RouterLink
          to="/"
          class="landing-brand"
        >
          <BrandLogo height="28px" />
        </RouterLink>

        <div class="landing-header-actions">
          <a
            :href="loginUrl"
            class="landing-header-link"
          >
            Logga in
          </a>
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
  align-items: center;
  justify-content: space-between;
  gap: var(--huleedu-space-4);
  width: 100%;
  max-width: var(--huleedu-max-width-6xl);
  margin: 0 auto;
  padding: var(--huleedu-space-4) var(--huleedu-space-6);
}

.landing-brand {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  cursor: pointer;
  text-decoration: none;
  user-select: none;
}

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
  color: var(--huleedu-navy);
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  cursor: pointer;
}

.landing-header-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: var(--huleedu-space-3);
}

.landing-brand:hover,
.landing-header-link:hover {
  color: var(--huleedu-action);
}

.landing-header-link:hover::after,
.landing-header-link:focus-visible::after {
  opacity: 1;
  transform: scaleX(1);
}

.landing-header-link:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--huleedu-action) 40%, transparent);
  outline-offset: 4px;
}

.landing-header-actions :deep(button) {
  position: relative;
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--huleedu-navy);
  font-family: inherit;
  font-size: var(--huleedu-text-sm);
  font-weight: var(--huleedu-font-semibold);
  line-height: 1.3;
  letter-spacing: normal;
  text-transform: none;
  cursor: pointer;
  transition:
    color var(--huleedu-duration-default) var(--huleedu-ease-default),
    opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.landing-header-actions :deep(button::after) {
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

.landing-header-actions :deep(button:hover) {
  color: var(--huleedu-action);
}

.landing-header-actions :deep(button:hover::after),
.landing-header-actions :deep(button:focus-visible::after) {
  opacity: 1;
  transform: scaleX(1);
}

.landing-header-actions :deep(button:focus-visible) {
  outline: 2px solid color-mix(in srgb, var(--huleedu-action) 40%, transparent);
  outline-offset: 4px;
}

.landing-header-actions :deep(button[aria-expanded="true"]) {
  color: var(--huleedu-action);
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
