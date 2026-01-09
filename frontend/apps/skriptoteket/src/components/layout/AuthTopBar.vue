<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import HelpButton from "../help/HelpButton.vue";

const props = defineProps<{
  user: { email: string; role: string } | null;
  logoutInProgress: boolean;
  isFocusMode: boolean;
}>();

const emit = defineEmits<{
  logout: [];
  toggleFocusMode: [];
}>();

const route = useRoute();
const navLink = computed(() => {
  if (!props.isFocusMode) {
    return null;
  }
  if (route.name === "admin-tool-editor" || route.name === "admin-tool-version-editor") {
    return {
      to: "/admin/tools",
      label: "← Tillbaka till verktyg",
    };
  }
  return null;
});

function onLogout(): void {
  emit("logout");
}

function onToggleFocusMode(): void {
  emit("toggleFocusMode");
}
</script>

<template>
  <header class="top-user-bar">
    <div class="top-user-bar-left">
      <RouterLink
        v-if="navLink"
        :to="navLink.to"
        class="top-nav-link"
      >
        {{ navLink.label }}
      </RouterLink>
    </div>
    <div class="top-user-bar-right">
      <button
        type="button"
        class="btn-ghost"
        :aria-pressed="isFocusMode"
        @click="onToggleFocusMode"
      >
        <span v-if="isFocusMode">Avsluta fokusl&auml;ge</span>
        <span v-else>Aktivera fokusl&auml;ge</span>
      </button>
      <HelpButton />
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
</template>

<style scoped>
.top-user-bar {
  display: none;
  align-items: center;
  justify-content: space-between;
  padding: var(--huleedu-space-3) var(--huleedu-space-6);
  border-bottom: var(--huleedu-border-width) solid var(--huleedu-navy);
  background-color: var(--huleedu-canvas);
  color: var(--huleedu-navy);
  position: sticky;
  top: 0;
  z-index: 30;
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

.top-nav-link {
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy);
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.top-nav-link:hover {
  color: var(--huleedu-burgundy);
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
</style>
