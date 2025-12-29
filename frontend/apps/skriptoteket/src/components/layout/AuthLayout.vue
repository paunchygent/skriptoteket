<script setup lang="ts">
import { ref } from "vue";
import { RouterLink } from "vue-router";

import AuthSidebar from "./AuthSidebar.vue";
import AuthTopBar from "./AuthTopBar.vue";

defineProps<{
  user: { email: string; role: string } | null;
  canSeeContributor: boolean;
  canSeeAdmin: boolean;
  logoutError: string | null;
  logoutInProgress: boolean;
}>();

const emit = defineEmits<{
  logout: [];
}>();

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
</script>

<template>
  <!-- Mobile header bar: brand left, hamburger right -->
  <header class="auth-mobile-header md:hidden">
    <RouterLink
      to="/"
      class="mobile-brand"
    >
      Skriptoteket
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
  <Transition name="drawer-backdrop">
    <div
      v-if="sidebarOpen"
      class="md:hidden fixed inset-0 bg-navy/40 z-40"
      @click="closeSidebar"
    />
  </Transition>

  <!-- Sidebar (authenticated) -->
  <AuthSidebar
    :is-open="sidebarOpen"
    :user="user"
    :can-see-contributor="canSeeContributor"
    :can-see-admin="canSeeAdmin"
    :logout-in-progress="logoutInProgress"
    @close="closeSidebar"
    @logout="onLogout"
  />

  <!-- Main content wrapper with top user bar -->
  <div class="auth-main-wrapper">
    <!-- Top user bar -->
    <AuthTopBar
      :user="user"
      :logout-in-progress="logoutInProgress"
      @logout="onLogout"
    />

    <!-- Main content area -->
    <main class="auth-main-content">
      <div
        v-if="logoutError"
        class="mb-4 p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
      >
        {{ logoutError }}
      </div>
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
}

/* Main wrapper (authenticated) */
.auth-main-wrapper {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

@media (min-width: 768px) {
  .auth-main-wrapper {
    margin-left: var(--huleedu-sidebar-width);
  }
}

/* Main content (authenticated) */
.auth-main-content {
  flex: 1;
  padding: var(--huleedu-space-6);
  overflow-y: auto;
  scrollbar-gutter: stable;
}

@media (min-width: 768px) {
  .auth-main-content {
    padding: var(--huleedu-space-8);
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
