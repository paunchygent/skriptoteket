<script setup lang="ts">
/**
 * Authenticated top bar.
 *
 * This bar remains available across authenticated routes, but immersive game
 * routes simplify it to the essentials so the platform chrome does not compete
 * with bespoke game presentation.
 */

import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

import BrandLogo from "../brand/BrandLogo.vue";
import HelpButton from "../help/HelpButton.vue";

const emit = defineEmits<{
  logout: [];
  toggleFocusMode: [];
}>();

const route = useRoute();
const props = defineProps<{
  user: { email: string; role: string } | null;
  logoutInProgress: boolean;
  isFocusMode: boolean;
  isImmersiveRoute: boolean;
}>();

const navLink = computed(() => {
  if (props.isImmersiveRoute) {
    return {
      to: "/browse",
      label: "← Tillbaka till katalogen",
    };
  }
  if (route.name === "admin-tool-editor" || route.name === "admin-tool-version-editor") {
    return {
      to: "/admin/tools",
      label: "← Tillbaka till verktyg",
    };
  }
  return null;
});

const shouldShowBrand = computed(() => props.isFocusMode || props.isImmersiveRoute);

function onLogout(): void {
  emit("logout");
}

function onToggleFocusMode(): void {
  emit("toggleFocusMode");
}
</script>

<template>
  <header
    class="top-user-bar"
    :class="{ 'top-user-bar--immersive': isImmersiveRoute }"
  >
    <div class="top-user-bar-left">
      <div class="topbar-brand-slot">
        <div
          class="topbar-brand-spacer"
          aria-hidden="true"
        />
        <Transition name="topbar-brand">
          <RouterLink
            v-if="shouldShowBrand"
            to="/"
            class="topbar-brand-link"
            aria-label="Skriptoteket"
          >
            <BrandLogo height="32px" />
          </RouterLink>
        </Transition>
      </div>
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
        v-if="!isImmersiveRoute"
        type="button"
        class="focus-mode-toggle"
        :class="{ 'is-active': isFocusMode }"
        :aria-pressed="isFocusMode"
        @click="onToggleFocusMode"
      >
        <Transition
          name="focus-toggle-label"
          mode="out-in"
        >
          <span :key="isFocusMode ? 'active' : 'inactive'">
            <span
              v-if="isFocusMode"
              class="focus-toggle-active-label"
            >Avsluta fokusl&auml;ge</span>
            <span v-else>Aktivera fokusl&auml;ge</span>
          </span>
        </Transition>
      </button>
      <HelpButton />
      <span
        v-if="!isImmersiveRoute"
        class="user-separator"
      >|</span>
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

.top-user-bar--immersive {
  background: linear-gradient(180deg, rgba(18, 27, 24, 0.96), rgba(13, 18, 16, 0.9));
  backdrop-filter: blur(18px);
  color: var(--huleedu-canvas);
}

.top-user-bar-left {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-4);
}

.top-user-bar-right {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-3);
}

.topbar-brand-slot {
  position: relative;
  display: inline-flex;
  align-items: center;
  height: 32px;
}

.topbar-brand-spacer {
  aspect-ratio: 2100 / 460;
  height: 32px;
  flex: 0 0 auto;
}

.topbar-brand-link {
  position: absolute;
  inset: 0;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  text-decoration: none;
}

.topbar-brand-link:focus-visible {
  outline: 2px solid var(--huleedu-burgundy-40);
  outline-offset: 3px;
}

.topbar-brand-enter-active,
.topbar-brand-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.topbar-brand-enter-from,
.topbar-brand-leave-to {
  opacity: 0;
}

.focus-mode-toggle {
  padding: var(--huleedu-space-1) var(--huleedu-space-3);
  border: var(--huleedu-border-width) solid var(--huleedu-navy-30);
  background-color: white;
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  text-transform: uppercase;
  letter-spacing: var(--huleedu-tracking-label);
  color: var(--huleedu-navy);
  cursor: pointer;
  user-select: none;
  transition:
    background-color var(--huleedu-duration-default) var(--huleedu-ease-default),
    border-color var(--huleedu-duration-default) var(--huleedu-ease-default),
    color var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.focus-mode-toggle:hover {
  border-color: var(--huleedu-navy);
  color: var(--huleedu-burgundy);
}

.focus-mode-toggle.is-active {
  border-color: var(--huleedu-burgundy);
  color: var(--huleedu-burgundy);
}

.focus-mode-toggle:focus-visible {
  outline: 2px solid var(--huleedu-burgundy-40);
  outline-offset: 3px;
}

.focus-toggle-label-enter-active,
.focus-toggle-label-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}

.focus-toggle-label-enter-from,
.focus-toggle-label-leave-to {
  opacity: 0;
}

.focus-toggle-active-label {
  display: inline-block;
  padding-inline: calc((var(--huleedu-space-2) + var(--huleedu-border-width)) / 2);
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

.top-user-bar--immersive .top-nav-link,
.top-user-bar--immersive .logout-btn,
.top-user-bar--immersive .user-separator {
  color: var(--huleedu-canvas);
}

.top-user-bar--immersive .top-nav-link:hover,
.top-user-bar--immersive .logout-btn:hover {
  color: #efc06c;
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
