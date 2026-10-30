<script setup lang="ts">
/**
 * Signed-out public frame.
 *
 * Relationships:
 * - the same 56 px top bar as the signed-in shell, without a sidebar: the
 *   shared logo link at the left, Logga in and Hjälp as ghost buttons at the
 *   right
 * - Logga in opens the HuleEdu ceremony directly with the route's continuation
 * - the page frame is centred at 1040 px with the signed-in frame's padding;
 *   route-level hero surfaces own the strongest next step
 * - public documents.conversion_hub routes fill the frame
 *   (landing-main--workspace / landing-frame--workspace); other routes keep
 *   the 1040 px column
 */

import { computed } from "vue";
import { useRoute } from "vue-router";

import { sharedAuthCeremonyUrl } from "../../api/sharedAuth";
import { resolveLandingAuthContinuation } from "../../composables/auth/authEntryNavigation";
import BrandHomeLink from "../brand/BrandHomeLink.vue";
import ShellBarButton from "./ShellBarButton.vue";
import ShellHelpButton from "./ShellHelpButton.vue";

const route = useRoute();
const FULL_FRAME_PUBLIC_APP_IDS = new Set(["documents.conversion_hub"]);

const isFullFrameWorkspaceRoute = computed(() => {
  if (route.name !== "public-app-capability-detail" && route.name !== "public-app-detail") {
    return false;
  }

  const appId = route.params.appId;
  return typeof appId === "string" && FULL_FRAME_PUBLIC_APP_IDS.has(appId);
});
const loginUrl = computed(() => {
  const continuation = resolveLandingAuthContinuation(route);
  return sharedAuthCeremonyUrl({
    nextPath: continuation.nextPath,
    origin: window.location.origin,
  });
});
</script>

<template>
  <div
    class="landing-shell"
    :class="{ 'landing-shell--workspace': isFullFrameWorkspaceRoute }"
  >
    <header class="landing-topbar">
      <BrandHomeLink class="landing-brand" />

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

    <main
      class="landing-main"
      :class="{ 'landing-main--workspace': isFullFrameWorkspaceRoute }"
    >
      <div
        class="landing-frame"
        :class="{ 'landing-frame--workspace': isFullFrameWorkspaceRoute }"
      >
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

/* The guest workspace is held to the window at every viewport width
   (walk G1): the shell takes the window height and clips, so the panels
   scroll inside instead of the page growing with its content. Other public
   routes keep the growing min-height column. */
.landing-shell--workspace {
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
}

/* The slotted route stage fills the held frame the way the signed-in shell
   holds its route stage (AuthLayout .auth-main-content--exam-workspace). */
.landing-shell--workspace :deep(.route-stage),
.landing-shell--workspace :deep(.route-stage-item) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
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
  }

  .landing-main {
    padding: var(--huleedu-space-8);
  }
}

/* The guest workspace fills the frame on desktop only (TASK-SKRIPT-41-02-04):
   tablet and phone keep the existing centred guest frame. */
@media (min-width: 1280px) {
  .landing-main.landing-main--workspace {
    padding: 0;
  }

  .landing-frame.landing-frame--workspace {
    max-width: none;
    margin: 0;
  }
}
</style>
