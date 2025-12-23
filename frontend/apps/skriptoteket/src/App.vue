<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useLoginModal } from "./composables/useLoginModal";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const loginModal = useLoginModal();

const logoutError = ref<string | null>(null);
const logoutInProgress = ref(false);
const sidebarOpen = ref(false);

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value;
}

function closeSidebar() {
  sidebarOpen.value = false;
}

// Login modal form state
const email = ref("");
const password = ref("");
const submitError = ref<string | null>(null);
const isSubmitting = computed(() => auth.status === "loading");

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));

onMounted(() => {
  void auth.bootstrap();
});

const isProtectedRoute = computed(() => {
  return route.matched.some((record) => {
    if (record.meta.requiresAuth) {
      return true;
    }
    return typeof record.meta.minRole === "string";
  });
});

function closeLoginModal() {
  loginModal.close();
  email.value = "";
  password.value = "";
  submitError.value = null;
}

async function onLoginSubmit(): Promise<void> {
  submitError.value = null;
  try {
    await auth.login({ email: email.value, password: password.value });
    const redirect = loginModal.redirectTo.value;
    closeLoginModal();
    if (redirect) {
      router.push(redirect);
    }
  } catch (error: unknown) {
    submitError.value = error instanceof Error ? error.message : "Inloggningen misslyckades";
  }
}

watch(
  () => auth.isAuthenticated,
  async (value) => {
    if (value) {
      return;
    }
    if (logoutInProgress.value) {
      return;
    }
    if (!isProtectedRoute.value) {
      return;
    }
    if (route.name === "login") {
      return;
    }

    await router.replace({
      name: "login",
      query: { next: route.fullPath },
    });
  },
);

async function onLogout(): Promise<void> {
  logoutError.value = null;
  logoutInProgress.value = true;

  try {
    await auth.logout();
    await router.push({ path: "/" });
  } catch (error: unknown) {
    logoutError.value = error instanceof Error ? error.message : "Logout failed";
  } finally {
    logoutInProgress.value = false;
  }
}
</script>

<template>
  <div class="app-layout min-h-screen text-navy">
    <!-- ═══════════════════════════════════════════════════════════════════════
         UNAUTHENTICATED LAYOUT: Horizontal top nav
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-if="!isAuthenticated">
      <!-- Landing header: Logo only, no nav links -->
      <header class="landing-header">
        <div class="landing-header-inner">
          <RouterLink
            to="/"
            class="landing-brand"
          >
            Skriptoteket
          </RouterLink>
        </div>
      </header>

      <!-- Landing main content -->
      <main class="landing-main">
        <RouterView />
      </main>
    </template>

    <!-- ═══════════════════════════════════════════════════════════════════════
         AUTHENTICATED LAYOUT: Sidebar + Top user bar
         ═══════════════════════════════════════════════════════════════════════ -->
    <template v-else>
      <!-- Mobile header bar: hamburger only (right-aligned) -->
      <header class="auth-mobile-header md:hidden">
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
      <aside
        class="sidebar"
        :class="{ 'is-open': sidebarOpen }"
      >
        <div class="sidebar-content">
          <RouterLink
            to="/"
            class="sidebar-brand"
            @click="closeSidebar"
          >
            Skriptoteket
          </RouterLink>

          <nav class="sidebar-nav">
            <RouterLink
              to="/"
              class="sidebar-nav-item"
              @click="closeSidebar"
            >
              Hem
            </RouterLink>
            <RouterLink
              to="/browse"
              class="sidebar-nav-item"
              @click="closeSidebar"
            >
              Katalog
            </RouterLink>
            <RouterLink
              to="/my-runs"
              class="sidebar-nav-item"
              @click="closeSidebar"
            >
              Mina körningar
            </RouterLink>
            <RouterLink
              v-if="canSeeContributor"
              to="/my-tools"
              class="sidebar-nav-item"
              @click="closeSidebar"
            >
              Mina verktyg
            </RouterLink>
            <RouterLink
              v-if="canSeeAdmin"
              to="/admin/tools"
              class="sidebar-nav-item"
              @click="closeSidebar"
            >
              Admin
            </RouterLink>
          </nav>

          <!-- Sidebar footer: user info + logout (mobile only) -->
          <div class="sidebar-footer md:hidden">
            <div class="sidebar-user-info">
              {{ auth.user?.email }}
            </div>
            <button
              type="button"
              class="sidebar-logout-btn"
              :disabled="logoutInProgress"
              @click="onLogout"
            >
              {{ logoutInProgress ? "Loggar ut…" : "Logga ut" }}
            </button>
          </div>
        </div>
      </aside>

      <!-- Main content wrapper with top user bar -->
      <div class="auth-main-wrapper">
        <!-- Top user bar -->
        <header class="top-user-bar">
          <div class="top-user-bar-left">
            <!-- Future: breadcrumb or page title -->
          </div>
          <div class="top-user-bar-right">
            <span class="user-info">
              {{ auth.user?.email }}
              <span class="user-role">({{ auth.user?.role }})</span>
            </span>
            <span class="user-separator">|</span>
            <button
              type="button"
              class="logout-btn"
              :disabled="logoutInProgress"
              @click="onLogout"
            >
              {{ logoutInProgress ? "Loggar ut…" : "Logga ut" }}
            </button>
          </div>
        </header>

        <!-- Main content area -->
        <main class="auth-main-content">
          <div
            v-if="logoutError"
            class="mb-4 p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
          >
            {{ logoutError }}
          </div>
          <RouterView />
        </main>
      </div>
    </template>

    <!-- Global Login Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="loginModal.isOpen.value"
          class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
          role="dialog"
          aria-modal="true"
          aria-labelledby="login-modal-title"
          :aria-describedby="submitError ? 'login-modal-error' : undefined"
          @click.self="closeLoginModal"
        >
          <div
            class="relative w-full max-w-sm mx-4 p-6 bg-canvas border border-navy shadow-brutal"
          >
            <button
              type="button"
              class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
              @click="closeLoginModal"
            >
              &times;
            </button>

            <h2
              id="login-modal-title"
              class="text-xl font-semibold text-navy"
            >
              Logga in
            </h2>

            <div
              v-if="submitError"
              id="login-modal-error"
              class="mt-4 p-3 border border-error bg-white text-error text-sm"
            >
              {{ submitError }}
            </div>

            <form
              class="mt-5 space-y-4"
              @submit.prevent="onLoginSubmit"
            >
              <div>
                <label
                  class="block text-sm font-semibold text-navy mb-1"
                  for="modal-email"
                >
                  E-post
                </label>
                <input
                  id="modal-email"
                  v-model="email"
                  type="email"
                  autocomplete="username"
                  required
                  class="w-full px-3 py-2 border border-navy bg-white text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <div>
                <label
                  class="block text-sm font-semibold text-navy mb-1"
                  for="modal-password"
                >
                  Lösenord
                </label>
                <input
                  id="modal-password"
                  v-model="password"
                  type="password"
                  autocomplete="current-password"
                  required
                  class="w-full px-3 py-2 border border-navy bg-white text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <button
                type="submit"
                class="w-full px-4 py-2 bg-navy text-canvas border border-navy font-semibold uppercase tracking-wide hover:bg-burgundy transition-colors disabled:opacity-50"
                :disabled="isSubmitting"
              >
                {{ isSubmitting ? "Loggar in…" : "Logga in" }}
              </button>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════════════════════════════════
   APP LAYOUT BASE
   ═══════════════════════════════════════════════════════════════════════════ */
.app-layout {
  min-height: 100vh;
}

/* ═══════════════════════════════════════════════════════════════════════════
   LANDING LAYOUT (Unauthenticated)
   ═══════════════════════════════════════════════════════════════════════════ */
.landing-header {
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
}

.landing-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: var(--huleedu-max-width-6xl);
  margin: 0 auto;
  padding: var(--huleedu-space-4) var(--huleedu-space-6);
  gap: var(--huleedu-space-4);
}

.landing-brand {
  font-family: var(--huleedu-font-serif);
  font-weight: var(--huleedu-font-bold);
  font-size: var(--huleedu-text-xl);
  letter-spacing: var(--huleedu-tracking-tight);
  color: var(--huleedu-navy);
  text-decoration: none;
}

.landing-brand:hover {
  color: var(--huleedu-burgundy);
}

.landing-main {
  max-width: var(--huleedu-max-width-6xl);
  margin: 0 auto;
  padding: var(--huleedu-space-8) var(--huleedu-space-6);
}

/* ═══════════════════════════════════════════════════════════════════════════
   AUTHENTICATED LAYOUT (Sidebar + Top bar)
   ═══════════════════════════════════════════════════════════════════════════ */

/* Mobile header for authenticated - hidden on desktop */
.auth-mobile-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: var(--huleedu-space-3) var(--huleedu-space-4);
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
}

@media (min-width: 768px) {
  .auth-mobile-header {
    display: none;
  }
}

/* Sidebar */
.sidebar {
  display: none;
  flex-direction: column;
  border-right: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--huleedu-sidebar-width);
  z-index: var(--huleedu-z-popover);
  transform: translateX(-100%);
  transition: transform var(--huleedu-duration-slow) var(--huleedu-ease-out);
}

.sidebar.is-open {
  display: flex;
  transform: translateX(0);
}

@media (min-width: 768px) {
  .sidebar {
    display: flex;
    position: fixed;
    transform: none;
    z-index: var(--huleedu-z-overlay);
  }
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--huleedu-space-6) var(--huleedu-space-4);
}

.sidebar-brand {
  font-family: var(--huleedu-font-serif);
  font-weight: var(--huleedu-font-bold);
  font-size: var(--huleedu-text-lg);
  letter-spacing: var(--huleedu-tracking-tight);
  color: var(--huleedu-navy);
  text-decoration: none;
  margin-bottom: var(--huleedu-space-8);
}

.sidebar-brand:hover {
  color: var(--huleedu-burgundy);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-1);
  flex: 1;
}

.sidebar-nav-item {
  display: block;
  padding: var(--huleedu-space-2) var(--huleedu-space-3);
  font-size: var(--huleedu-text-sm);
  font-weight: var(--huleedu-font-medium);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy-70);
  text-decoration: none;
  border-left: var(--huleedu-border-width-2) solid transparent;
  transition: color var(--huleedu-duration-default) var(--huleedu-ease-default),
              border-color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.sidebar-nav-item:hover {
  color: var(--huleedu-burgundy);
}

.sidebar-nav-item.router-link-active {
  color: var(--huleedu-navy);
  border-left-color: var(--huleedu-burgundy);
}

/* Sidebar footer (mobile only) */
.sidebar-footer {
  margin-top: auto;
  padding-top: var(--huleedu-space-4);
  border-top: var(--huleedu-border-width) solid var(--huleedu-navy-20);
}

.sidebar-user-info {
  font-size: var(--huleedu-text-xs);
  font-family: var(--huleedu-font-mono);
  color: var(--huleedu-navy);
  margin-bottom: var(--huleedu-space-2);
  word-break: break-all;
}

.sidebar-logout-btn {
  display: block;
  width: 100%;
  padding: var(--huleedu-space-2) var(--huleedu-space-3);
  border: var(--huleedu-border-width) solid var(--huleedu-navy);
  background: transparent;
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy);
  cursor: pointer;
  text-align: center;
  transition: background-color var(--huleedu-duration-default) var(--huleedu-ease-default),
              color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.sidebar-logout-btn:hover {
  background-color: var(--huleedu-navy);
  color: var(--huleedu-canvas);
}

.sidebar-logout-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

/* Top user bar */
.top-user-bar {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: var(--huleedu-space-3) var(--huleedu-space-6);
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
  color: var(--huleedu-navy);
}

@media (min-width: 768px) {
  .top-user-bar {
    display: flex;
  }
}

.top-user-bar-left {
  /* Future: breadcrumb */
}

.top-user-bar-right {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-3);
}

.user-info {
  font-size: var(--huleedu-text-xs);
  font-family: var(--huleedu-font-mono);
  color: var(--huleedu-navy);
}

.user-role {
  opacity: 0.6;
}

.user-separator {
  color: var(--huleedu-navy);
  opacity: 0.3;
}

.logout-btn {
  padding: var(--huleedu-space-1) var(--huleedu-space-2);
  border: none;
  background: none;
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy);
  cursor: pointer;
  transition: color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.logout-btn:hover {
  color: var(--huleedu-burgundy);
}

.logout-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Main content (authenticated) */
.auth-main-content {
  flex: 1;
  padding: var(--huleedu-space-6);
  overflow-y: auto;
}

@media (min-width: 768px) {
  .auth-main-content {
    padding: var(--huleedu-space-8);
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   SHARED: Hamburger button
   ═══════════════════════════════════════════════════════════════════════════ */
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

/* ═══════════════════════════════════════════════════════════════════════════
   TRANSITIONS
   ═══════════════════════════════════════════════════════════════════════════ */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.drawer-backdrop-enter-active,
.drawer-backdrop-leave-active {
  transition: opacity var(--huleedu-duration-slow) var(--huleedu-ease-default);
}
.drawer-backdrop-enter-from,
.drawer-backdrop-leave-to {
  opacity: 0;
}
</style>
