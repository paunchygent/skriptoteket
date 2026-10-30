<script setup lang="ts">
/**
 * Signed-in top bar: one 56 px bar at every width.
 *
 * Relationships:
 * - `AuthLayout` places it in the shell grid and owns the sidebar, focus-mode
 *   and drawer state; this bar only emits the toggles
 * - desktop (>= 1280 px): sidebar toggle, brand, Fokusläge, Hjälp, Logga ut
 *   with words; tablet: the same actions glyph-only and no sidebar toggle;
 *   phone (< 768 px): brand and Meny, with the actions in the Meny drawer
 * - `#app-topbar-page-slot` is the phone page slot: a route teleports its title
 *   and primary action into it, and the brand hides while it has content
 *   (contract with the exam workspace, TASK-SKRIPT-40-04-03)
 * - immersive game routes get a dark bar with the way back to the catalogue,
 *   Hjälp and Logga ut at every width, because they have no sidebar or drawer
 */

import { computed, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";

import { UiGlyph } from "../ui";
import BrandHomeLink from "../brand/BrandHomeLink.vue";
import ShellBarButton from "./ShellBarButton.vue";
import ShellHelpButton from "./ShellHelpButton.vue";

const props = defineProps<{
  logoutInProgress: boolean;
  isFocusMode: boolean;
  isSidebarCollapsed: boolean;
  isImmersiveRoute: boolean;
  isMenuOpen: boolean;
}>();

const emit = defineEmits<{
  logout: [];
  toggleFocusMode: [];
  toggleSidebar: [];
  toggleMenu: [];
}>();

const route = useRoute();
const menuButtonRef = ref<InstanceType<typeof ShellBarButton> | null>(null);

const appLabel = computed(() => (route.name === "exam-workspace" ? "Provredigering" : null));

const backLink = computed(() => {
  if (props.isImmersiveRoute) {
    return { to: "/browse", label: "Tillbaka till katalogen" };
  }
  if (route.name === "admin-tool-editor" || route.name === "admin-tool-version-editor") {
    return { to: "/admin/tools", label: "Tillbaka till verktyg" };
  }
  return null;
});

const sidebarToggleLabel = computed(() =>
  props.isSidebarCollapsed ? "Fäll ut menyn" : "Fäll ihop menyn",
);
const focusModeLabel = computed(() =>
  props.isFocusMode ? "Avsluta fokusläge" : "Aktivera fokusläge",
);
const logoutLabel = computed(() => (props.logoutInProgress ? "Loggar ut…" : "Logga ut"));

function menuButtonElement(): HTMLElement | null {
  const element = menuButtonRef.value?.$el;
  return element instanceof HTMLElement ? element : null;
}

defineExpose({ menuButtonElement });
</script>

<template>
  <header
    class="topbar"
    :class="{ 'topbar--immersive': isImmersiveRoute, 'topbar--focus-mode': isFocusMode }"
  >
    <ShellBarButton
      v-if="!isImmersiveRoute"
      class="topbar-sidebar-toggle"
      glyph="toggle-sidebar"
      :label="sidebarToggleLabel"
      word-from="never"
      :pressed="isSidebarCollapsed"
      aria-controls="app-sidebar"
      @click="emit('toggleSidebar')"
    />

    <BrandHomeLink class="topbar-brand">
      <small
        v-if="appLabel"
        class="topbar-brand-app"
      >{{ appLabel }}</small>
    </BrandHomeLink>

    <RouterLink
      v-if="backLink"
      :to="backLink.to"
      class="topbar-back-link"
      :title="backLink.label"
    >
      <UiGlyph
        meaning="back"
        :size="16"
      />
      <span class="topbar-back-link__label">{{ backLink.label }}</span>
    </RouterLink>

    <div
      id="app-topbar-page-slot"
      class="topbar-page-slot"
    />

    <span
      class="topbar-grow"
      aria-hidden="true"
    />

    <ShellBarButton
      v-if="!isImmersiveRoute"
      class="topbar-action topbar-focus-toggle"
      glyph="focus-mode"
      :label="focusModeLabel"
      word="Fokusläge"
      :pressed="isFocusMode"
      @click="emit('toggleFocusMode')"
    />
    <ShellHelpButton class="topbar-action topbar-help" />
    <ShellBarButton
      class="topbar-action topbar-logout"
      glyph="log-out"
      :label="logoutLabel"
      :word="logoutLabel"
      word-reserve="Loggar ut…"
      :disabled="logoutInProgress"
      @click="emit('logout')"
    />

    <ShellBarButton
      v-if="!isImmersiveRoute"
      ref="menuButtonRef"
      class="topbar-menu-button"
      glyph="navigation-menu"
      label="Meny"
      word-from="never"
      aria-controls="app-sidebar"
      :aria-expanded="isMenuOpen"
      @click="emit('toggleMenu')"
    />
  </header>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  gap: var(--huleedu-space-2);
  min-width: 0;
  height: var(--shell-top, 56px);
  padding: 0 var(--huleedu-space-4);
  border-bottom: 1px solid var(--huleedu-surface-divider);
  background: var(--huleedu-canvas);
  color: var(--huleedu-navy);
}

/* Both bars use `BrandHomeLink`, whose `--huleedu-space-10` (40px) logo keeps
   the wordmark's visible ink (35px) above the 20 px page title inside the 56 px
   bar, and whose 44 px action-control height keeps the home link a full touch
   target. This class adds only the signed-in bar's spacing. */
.topbar-brand {
  margin-left: var(--huleedu-space-2);
}

.topbar-back-link:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: 2px;
  border-radius: var(--huleedu-radius-md);
}

.topbar-brand-app {
  color: var(--huleedu-terracotta);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-bold);
}

.topbar-back-link {
  display: inline-flex;
  align-items: center;
  gap: var(--huleedu-space-1-5);
  min-width: 0;
  min-height: 44px;
  padding: 0 var(--huleedu-space-2);
  color: var(--huleedu-navy-70);
  font-size: var(--huleedu-text-sm);
  font-weight: var(--huleedu-font-medium);
  text-decoration: none;
}

.topbar-back-link__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (hover: hover) {
  .topbar-back-link:hover {
    color: var(--huleedu-action);
  }
}

.topbar-page-slot {
  display: none;
}

.topbar-grow {
  flex: 1;
  min-width: 0;
}

/* The sidebar toggle shows its state through its glyph and name only; the
   pressed fill would read as an active mode. */
.topbar .topbar-sidebar-toggle[aria-pressed="true"] {
  border-color: transparent;
  background: transparent;
  color: inherit;
}

/* Tablet: the rail cannot expand, so the toggle goes. */
@media (max-width: 1279px) {
  .topbar-sidebar-toggle {
    display: none;
  }
}

/* Focus mode makes the toggle unavailable but keeps its slot, so the brand
   holds still; a visibility-hidden button is not focusable. */
.topbar--focus-mode .topbar-sidebar-toggle {
  visibility: hidden;
}

.topbar-menu-button {
  display: none;
}

/* Phone: brand (or the route's page slot) and Meny; the actions live in the
   Meny drawer. */
@media (max-width: 767px) {
  .topbar {
    padding: 0 var(--huleedu-space-2) 0 var(--huleedu-space-4);
  }

  .topbar-brand {
    margin: 0;
  }

  .topbar-page-slot {
    display: flex;
    flex: 1;
    align-items: center;
    gap: var(--huleedu-space-2);
    min-width: 0;
  }

  .topbar-page-slot:empty {
    display: none;
  }

  .topbar:has(.topbar-page-slot:not(:empty)) .topbar-brand,
  .topbar:has(.topbar-page-slot:not(:empty)) .topbar-grow {
    display: none;
  }

  .topbar:not(.topbar--immersive) .topbar-action {
    display: none;
  }

  .topbar-menu-button {
    display: inline-flex;
  }
}

/* Immersive game routes: dark bar over the game, no sidebar or drawer. */
/* No shared role exists for dark chrome, so the bar darkens the action teal
   toward black; text and hover derive from the canvas roles. */
.topbar--immersive {
  border-bottom-color: var(--huleedu-canvas-15);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--huleedu-action) 22%, black),
    color-mix(in srgb, var(--huleedu-action) 14%, black)
  );
  color: var(--huleedu-canvas);
}

/* The wordmark's ink is navy, so the dark bar points the logo's two wordmark
   tokens at the light roles instead of filtering the artwork. */
.topbar--immersive .topbar-brand {
  --huleedu-wordmark-primary: var(--huleedu-canvas);
  --huleedu-wordmark-accent: var(--huleedu-canvas-80);
}

.topbar--immersive .topbar-back-link {
  color: var(--huleedu-canvas);
}

@media (hover: hover) {
  .topbar--immersive .topbar-back-link:hover,
  .topbar--immersive :deep(.shell-bar-button:not(:disabled):hover) {
    background: var(--huleedu-canvas-15);
    color: var(--huleedu-canvas);
  }
}

@media (max-width: 767px) {
  .topbar--immersive .topbar-brand {
    display: none;
  }
}
</style>
