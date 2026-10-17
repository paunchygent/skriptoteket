<script setup lang="ts">
/**
 * Signed-out public frame.
 *
 * Relationships:
 * - the same 56 px top bar as the signed-in shell, without a sidebar: the
 *   serif brand at the left, Logga in and Hjälp as ghost buttons at the right
 * - Logga in opens the HuleEdu ceremony directly with the route's continuation
 * - the page frame is centred at 1040 px with the signed-in frame's padding;
 *   route-level hero surfaces own the strongest next step
 */

import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { sharedAuthCeremonyUrl } from "../../api/sharedAuth";
import { resolveLandingAuthContinuation } from "../../composables/auth/authEntryNavigation";
import ShellBarButton from "./ShellBarButton.vue";
import ShellHelpButton from "./ShellHelpButton.vue";

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
    <header class="landing-topbar">
      <RouterLink
        to="/"
        class="landing-brand"
      >
        Skriptoteket
      </RouterLink>

      <div class="landing-header-actions">
        <ShellBarButton
          class="landing-header-link"
          label="Logga in"
          word="Logga in"
          word-from="always"
          :href="loginUrl"
        />
        <ShellHelpButton word-from="always" />
      </div>
    </header>

    <main class="landing-main">
      <div class="landing-frame">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.landing-shell {
  display: grid;
  grid-template-rows: 56px minmax(0, 1fr);
  min-height: 100vh;
  min-height: 100dvh;
}

.landing-topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--huleedu-space-2);
  min-width: 0;
  height: 56px;
  padding: 0 var(--huleedu-space-2) 0 var(--huleedu-space-4);
  border-bottom: 1px solid var(--huleedu-surface-divider);
  background: var(--huleedu-canvas);
  color: var(--huleedu-navy);
}

.landing-brand {
  flex: none;
  color: var(--huleedu-navy);
  font-family: var(--huleedu-font-serif);
  font-size: var(--huleedu-text-xl);
  font-weight: var(--huleedu-font-bold);
  line-height: 1;
  white-space: nowrap;
  text-decoration: none;
}

.landing-brand:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: 2px;
  border-radius: var(--huleedu-radius-md);
}

.landing-header-actions {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--huleedu-space-1);
}

.landing-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: var(--huleedu-space-5) var(--huleedu-space-4);
  background: var(--huleedu-canvas);
}

.landing-frame {
  display: flex;
  flex: 1;
  flex-direction: column;
  width: 100%;
  max-width: 1040px;
  min-height: 0;
  margin: 0 auto;
}

@media (min-width: 768px) {
  .landing-topbar {
    padding: 0 var(--huleedu-space-4);
  }

  .landing-brand {
    margin-left: var(--huleedu-space-2);
    font-size: var(--huleedu-text-2xl);
  }

  .landing-main {
    padding: var(--huleedu-space-8);
  }
}
</style>
