<script setup lang="ts">
/**
 * Authenticated application sidebar.
 *
 * Relationships:
 * - renders the shared authenticated navigation as either a drawer or fixed
 *   rail with utility/platform links first while authenticated home owns app
 *   entry affordances and the top auth bar owns help access
 * - lets planner routes defer the desktop rail until a wider `xl` breakpoint
 * - stays coordinated with `AuthLayout` so header, backdrop, and content margin
 *   all switch at the same shell cutoff
 */

import BrandLogo from "../brand/BrandLogo.vue";

type SidebarNavLink = {
  label: string;
  to: string;
};

const props = defineProps<{
  isOpen: boolean;
  isFocusMode: boolean;
  preferXlDesktopBreakpoint: boolean;
  user: { email: string } | null;
  canSeeContributor: boolean;
  canSeeAdmin: boolean;
  canSeeSuperuser: boolean;
  logoutInProgress: boolean;
}>();

const emit = defineEmits<{
  close: [];
  logout: [];
}>();

function onClose(): void {
  emit("close");
}

function onLogout(): void {
  emit("logout");
}

const standardLinks: readonly SidebarNavLink[] = [
  {
    label: "Hem",
    to: "/",
  },
  {
    label: "Mina filer",
    to: "/vault",
  },
  {
    label: "Föreslå verktyg",
    to: "/suggestions/new",
  },
  {
    label: "Katalog",
    to: "/browse",
  },
  {
    label: "Profil",
    to: "/profile",
  },
];
</script>

<template>
  <aside
    class="sidebar"
    :class="{
      'is-open': props.isOpen,
      'is-focus-mode': props.isFocusMode,
      'sidebar--xl-desktop-breakpoint': props.preferXlDesktopBreakpoint,
    }"
  >
    <div class="sidebar-content">
      <RouterLink
        to="/"
        class="sidebar-brand"
        @click="onClose"
      >
        <BrandLogo height="32px" />
      </RouterLink>

      <nav class="sidebar-nav">
        <RouterLink
          v-for="link in standardLinks"
          :key="link.to"
          :to="link.to"
          class="sidebar-nav-item"
          @click="onClose"
        >
          {{ link.label }}
        </RouterLink>
        <RouterLink
          v-if="props.canSeeContributor"
          to="/my-tools"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Mina verktyg
        </RouterLink>
        <RouterLink
          v-if="props.canSeeAdmin"
          to="/admin/tools"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Hantera verktyg
        </RouterLink>
        <RouterLink
          v-if="props.canSeeSuperuser"
          to="/admin/users"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Användare
        </RouterLink>
        <RouterLink
          v-if="props.canSeeAdmin"
          to="/admin/suggestions"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Granska förslag
        </RouterLink>
      </nav>

      <!-- Sidebar footer: user info + logout (mobile only) -->
      <div class="sidebar-footer md:hidden">
        <div class="sidebar-user-info">
          {{ props.user?.email }}
        </div>
        <button
          type="button"
          class="sidebar-logout-btn"
          :disabled="props.logoutInProgress"
          @click="onLogout"
        >
          {{ props.logoutInProgress ? "Loggar ut…" : "Logga ut" }}
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
/* Mobile: sidebar slides from right */
.sidebar {
  display: none;
  flex-direction: column;
  border-left: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: var(--huleedu-sidebar-width);
  z-index: var(--huleedu-z-popover);
  transform: translateX(100%);
  transition: transform var(--huleedu-duration-slow) var(--huleedu-ease-out);
}

.sidebar.is-open {
  display: flex;
  transform: translateX(0);
}

/* Desktop: sidebar fixed on left */
@media (min-width: 768px) {
  .sidebar:not(.sidebar--xl-desktop-breakpoint) {
    display: flex;
    position: fixed;
    left: 0;
    right: auto;
    border-left: none;
    border-right: var(--huleedu-border-width) solid var(--huleedu-navy);
    transform: none;
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    z-index: var(--huleedu-z-overlay);
    transition:
      opacity var(--huleedu-duration-slow) var(--huleedu-ease-default),
      visibility 0s linear 0s;
  }

  .sidebar:not(.sidebar--xl-desktop-breakpoint).is-focus-mode {
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transition:
      opacity var(--huleedu-duration-slow) var(--huleedu-ease-default),
      visibility 0s linear var(--huleedu-duration-slow);
  }
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: var(--huleedu-space-6) var(--huleedu-space-4);
}

@media (min-width: 768px) {
  .sidebar:not(.sidebar--xl-desktop-breakpoint) .sidebar-content {
    padding-top: var(--huleedu-space-3);
  }
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

@media (min-width: 768px) {
  .sidebar:not(.sidebar--xl-desktop-breakpoint) .sidebar-brand {
    transform: translateY(1px);
  }
}

.sidebar-brand:hover {
  color: var(--huleedu-action);
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
  color: var(--huleedu-action);
}

.sidebar-nav-item.router-link-active {
  color: var(--huleedu-navy);
  border-left-color: var(--huleedu-action);
}

@media (min-width: 1280px) {
  .sidebar.sidebar--xl-desktop-breakpoint {
    display: flex;
    position: fixed;
    left: 0;
    right: auto;
    border-left: none;
    border-right: var(--huleedu-border-width) solid var(--huleedu-navy);
    transform: none;
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
    z-index: var(--huleedu-z-overlay);
    transition:
      opacity var(--huleedu-duration-slow) var(--huleedu-ease-default),
      visibility 0s linear 0s;
  }

  .sidebar.sidebar--xl-desktop-breakpoint.is-focus-mode {
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    transition:
      opacity var(--huleedu-duration-slow) var(--huleedu-ease-default),
      visibility 0s linear var(--huleedu-duration-slow);
  }

  .sidebar.sidebar--xl-desktop-breakpoint .sidebar-content {
    padding-top: var(--huleedu-space-3);
  }

  .sidebar.sidebar--xl-desktop-breakpoint .sidebar-brand {
    transform: translateY(1px);
  }
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
</style>
