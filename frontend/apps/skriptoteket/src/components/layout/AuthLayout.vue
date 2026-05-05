<script setup lang="ts">
/**
 * Authenticated application layout.
 *
 * This layout usually renders the full Skriptoteket authenticated chrome, but
 * selected bespoke game routes can switch it into an immersive mode where only
 * the shared top bar remains and the generic sidebar framing disappears.
 */

import { computed, onBeforeUnmount, ref, watch, watchEffect } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { storeToRefs } from "pinia";

import BrandLogo from "../brand/BrandLogo.vue";
import AuthSidebar from "./AuthSidebar.vue";
import AuthTopBar from "./AuthTopBar.vue";
import { useLayoutStore } from "../../stores/layout";

const props = defineProps<{
  user: { id: string; email: string; role: string } | null;
  profile: { allow_remote_fallback?: boolean | null; inline_completion_provider?: "local" | "external" | null } | null;
  aiPolicy: {
    remote_providers_enabled: boolean;
    completion_external_available: boolean;
    completion_local_available: boolean;
  } | null;
  canSeeContributor: boolean;
  canSeeAdmin: boolean;
  canSeeSuperuser: boolean;
  logoutInProgress: boolean;
}>();

const emit = defineEmits<{
  logout: [];
}>();

const layout = useLayoutStore();
const { focusMode } = storeToRefs(layout);
const route = useRoute();
const IMMERSIVE_CURATED_APP_IDS = new Set(["games.flunk_out_frenzy"]);

const isEditorRoute = computed(
  () => route.name === "admin-tool-editor" || route.name === "admin-tool-version-editor",
);

const isImmersiveCuratedAppRoute = computed(() => {
  if (route.name !== "app-detail") {
    return false;
  }

  const appId = route.params.appId;
  return typeof appId === "string" && IMMERSIVE_CURATED_APP_IDS.has(appId);
});

const isClassroomPlannerRoute = computed(() => {
  return route.name === "app-detail" && route.params.appId === "classroom.group-seating-studio";
});
const prefersXlSidebarBreakpoint = computed(() => isClassroomPlannerRoute.value);

const sidebarOpen = ref(false);

function toggleSidebar(): void {
  sidebarOpen.value = !sidebarOpen.value;
}

function closeSidebar(): void {
  sidebarOpen.value = false;
}

function onLogout(): void {
  emit("logout");
}

function toggleFocusMode(): void {
  layout.toggle();
}

watch(
  () => props.user?.id ?? null,
  (userId) => {
    layout.hydrateForUser(userId);
  },
  { immediate: true },
);

watchEffect(() => {
  if (typeof document === "undefined") {
    return;
  }

  document.body.classList.toggle("app-shell-game-mode", isImmersiveCuratedAppRoute.value);
});

onBeforeUnmount(() => {
  if (typeof document !== "undefined") {
    document.body.classList.remove("app-shell-game-mode");
  }
});
</script>

<template>
  <!-- Mobile header bar: brand left, hamburger right -->
  <header
    v-if="!isImmersiveCuratedAppRoute"
    class="auth-mobile-header"
    :class="{ 'auth-mobile-header--xl-sidebar-breakpoint': prefersXlSidebarBreakpoint }"
  >
    <RouterLink
      to="/"
      class="mobile-brand"
    >
      <BrandLogo height="22px" />
    </RouterLink>
    <button
      type="button"
      class="hamburger"
      :class="{ 'is-open': sidebarOpen }"
      aria-label="Meny"
      :aria-expanded="sidebarOpen"
      @click="toggleSidebar"
    >
      <span /><span /><span />
    </button>
  </header>

  <!-- Mobile sidebar drawer backdrop -->
  <Transition
    v-if="!isImmersiveCuratedAppRoute"
    name="drawer-backdrop"
  >
    <div
      v-if="sidebarOpen"
      class="auth-sidebar-backdrop"
      :class="{ 'auth-sidebar-backdrop--xl-sidebar-breakpoint': prefersXlSidebarBreakpoint }"
      @click="closeSidebar"
    />
  </Transition>

  <!-- Sidebar (authenticated) -->
  <AuthSidebar
    v-if="!isImmersiveCuratedAppRoute"
    :is-open="sidebarOpen"
    :is-focus-mode="focusMode"
    :user="user"
    :can-see-contributor="canSeeContributor"
    :can-see-admin="canSeeAdmin"
    :can-see-superuser="canSeeSuperuser"
    :logout-in-progress="logoutInProgress"
    :prefer-xl-desktop-breakpoint="prefersXlSidebarBreakpoint"
    @close="closeSidebar"
    @logout="onLogout"
  />

  <!-- Main content wrapper with top user bar -->
  <div
    class="auth-main-wrapper"
    :class="{
      'is-focus-mode': focusMode,
      'is-immersive-route': isImmersiveCuratedAppRoute,
      'auth-main-wrapper--xl-sidebar-breakpoint': prefersXlSidebarBreakpoint,
    }"
  >
    <!-- Top user bar -->
    <AuthTopBar
      :user="user"
      :logout-in-progress="logoutInProgress"
      :is-focus-mode="focusMode"
      :is-immersive-route="isImmersiveCuratedAppRoute"
      :prefer-xl-desktop-breakpoint="prefersXlSidebarBreakpoint"
      @toggle-focus-mode="toggleFocusMode"
      @logout="onLogout"
    />

    <!-- Main content area -->
    <main
      class="auth-main-content"
      :class="{
        'auth-main-content--editor': isEditorRoute,
        'auth-main-content--workspace': isClassroomPlannerRoute,
        'auth-main-content--immersive': isImmersiveCuratedAppRoute,
      }"
    >
      <slot />
    </main>
  </div>
</template>

<style scoped>
/* Mobile header for authenticated - hidden on desktop */
.auth-mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--huleedu-space-3) var(--huleedu-space-4);
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
}

/* Mobile brand - no hover state since touch devices have sticky :hover */
.mobile-brand {
  font-family: var(--huleedu-font-serif);
  font-weight: var(--huleedu-font-bold);
  font-size: var(--huleedu-text-lg);
  letter-spacing: var(--huleedu-tracking-tight);
  color: var(--huleedu-navy);
  text-decoration: none;
}

@media (min-width: 768px) {
  .auth-mobile-header {
    display: none;
  }

  .auth-mobile-header.auth-mobile-header--xl-sidebar-breakpoint {
    display: flex;
  }
}

@media (min-width: 1280px) {
  .auth-mobile-header.auth-mobile-header--xl-sidebar-breakpoint {
    display: none;
  }
}

.auth-sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--huleedu-z-overlay);
  background-color: color-mix(in srgb, var(--huleedu-navy) 40%, transparent);
}

@media (min-width: 768px) {
  .auth-sidebar-backdrop {
    display: none;
  }

  .auth-sidebar-backdrop.auth-sidebar-backdrop--xl-sidebar-breakpoint {
    display: block;
  }
}

@media (min-width: 1280px) {
  .auth-sidebar-backdrop.auth-sidebar-backdrop--xl-sidebar-breakpoint {
    display: none;
  }
}

/* Main wrapper (authenticated) */
.auth-main-wrapper {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  min-height: 0;
  transition: margin-left var(--huleedu-duration-slow) var(--huleedu-ease-default);
}

@media (min-width: 768px) {
  .auth-main-wrapper:not(.auth-main-wrapper--xl-sidebar-breakpoint) {
    margin-left: var(--huleedu-sidebar-width);
    will-change: margin-left;
  }

  .auth-main-wrapper:not(.auth-main-wrapper--xl-sidebar-breakpoint).is-focus-mode,
  .auth-main-wrapper:not(.auth-main-wrapper--xl-sidebar-breakpoint).is-immersive-route {
    margin-left: 0;
  }
}

@media (min-width: 1280px) {
  .auth-main-wrapper.auth-main-wrapper--xl-sidebar-breakpoint {
    margin-left: var(--huleedu-sidebar-width);
    will-change: margin-left;
  }

  .auth-main-wrapper.auth-main-wrapper--xl-sidebar-breakpoint.is-focus-mode,
  .auth-main-wrapper.auth-main-wrapper--xl-sidebar-breakpoint.is-immersive-route {
    margin-left: 0;
  }
}

/* Main content (authenticated) */
.auth-main-content {
  flex: 1;
  min-height: 0;
  padding: var(--huleedu-space-6);
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.auth-main-content--editor {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
}

.auth-main-content--editor .route-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.auth-main-content--workspace {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-x: hidden;
}

.auth-main-content--workspace .route-stage,
.auth-main-content--workspace .route-stage-item {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.auth-main-content--editor .route-stage-item {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.auth-main-content--immersive {
  padding: 0;
  overflow: hidden;
}

.auth-main-content--immersive .route-stage,
.auth-main-content--immersive .route-stage-item {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

@media (min-width: 1024px) {
  .auth-main-content--editor {
    overflow: hidden;
  }
}

@media (min-width: 768px) {
  .auth-main-content {
    padding: var(--huleedu-space-8);
  }

  .auth-main-content--immersive {
    padding: 0;
  }
}

/* Hamburger button */
.hamburger {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 24px;
  height: 24px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.hamburger span {
  display: block;
  width: 100%;
  height: 2px;
  background-color: var(--huleedu-navy);
  transition: transform var(--huleedu-duration-slow) var(--huleedu-ease-default),
              opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}

.hamburger.is-open span:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}

.hamburger.is-open span:nth-child(2) {
  opacity: 0;
}

.hamburger.is-open span:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}

/* Transitions */
.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}
</style>
