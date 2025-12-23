<script setup lang="ts">
import { useHelp } from "../help/useHelp";

defineProps<{
  isOpen: boolean;
  user: { email: string } | null;
  canSeeContributor: boolean;
  canSeeAdmin: boolean;
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

const { open: openHelp } = useHelp();

function onHelp(): void {
  emit("close");
  openHelp();
}
</script>

<template>
  <aside
    class="sidebar"
    :class="{ 'is-open': isOpen }"
  >
    <div class="sidebar-content">
      <RouterLink
        to="/"
        class="sidebar-brand"
        @click="onClose"
      >
        Skriptoteket
      </RouterLink>

      <nav class="sidebar-nav">
        <button
          type="button"
          class="sidebar-nav-item sidebar-nav-button sidebar-nav-help"
          @click="onHelp"
        >
          Hjälp
        </button>
        <RouterLink
          to="/"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Hem
        </RouterLink>
        <RouterLink
          to="/browse"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Katalog
        </RouterLink>
        <RouterLink
          to="/my-runs"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Mina körningar
        </RouterLink>
        <RouterLink
          v-if="canSeeContributor"
          to="/my-tools"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Mina verktyg
        </RouterLink>
        <RouterLink
          v-if="canSeeContributor"
          to="/suggestions/new"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Föreslå verktyg
        </RouterLink>
        <RouterLink
          v-if="canSeeAdmin"
          to="/admin/tools"
          class="sidebar-nav-item"
          @click="onClose"
        >
          Admin
        </RouterLink>
        <RouterLink
          v-if="canSeeAdmin"
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
          {{ user?.email }}
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
  .sidebar {
    display: flex;
    position: fixed;
    left: 0;
    right: auto;
    border-left: none;
    border-right: var(--huleedu-border-width) solid var(--huleedu-navy);
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

.sidebar-nav-button {
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  cursor: pointer;
}

.sidebar-nav-help {
  display: block;
}

.sidebar-nav-help::after {
  content: none;
}

.sidebar-nav-item:hover {
  color: var(--huleedu-burgundy);
}

.sidebar-nav-item.router-link-active {
  color: var(--huleedu-navy);
  border-left-color: var(--huleedu-burgundy);
}

@media (min-width: 768px) {
  .sidebar-nav-help {
    display: none;
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
