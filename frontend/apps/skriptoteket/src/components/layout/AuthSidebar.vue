<script setup lang="ts">
/**
 * Signed-in navigation: sidebar, glyph rail or phone drawer.
 *
 * Relationships:
 * - `AuthLayout` places it in the shell grid and owns its open and rail state
 * - desktop (>= 1280 px): 240 px sidebar with labels, or the 64 px glyph rail
 *   when `isRail`; tablet: always the glyph rail; phone (< 768 px): a
 *   right-side drawer that Meny opens, with the user's email, Hjälp,
 *   Fokusläge and Logga ut in its footer
 * - the open phone drawer is keyboard-modal: Tab and Shift+Tab wrap inside it,
 *   and Escape, the close button and a selection dismiss it back to Meny
 * - the current page is marked by RouterLink's `aria-current="page"`
 * - utility links come first; the Administration section follows for admins
 *   and superusers. App entry points live on the home page, not here.
 */

import { computed, nextTick, ref, watch } from "vue";
import { RouterLink } from "vue-router";

import { UiGlyph, type UiGlyphMeaning } from "../ui";

type SidebarNavLink = {
  label: string;
  to: string;
  glyph: UiGlyphMeaning;
};

const props = defineProps<{
  isOpen: boolean;
  isRail: boolean;
  isFocusMode: boolean;
  user: { email: string } | null;
  canSeeContributor: boolean;
  canSeeAdmin: boolean;
  canSeeSuperuser: boolean;
  logoutInProgress: boolean;
}>();

const emit = defineEmits<{
  dismiss: [];
  help: [];
  logout: [];
  toggleFocusMode: [];
}>();

const navRef = ref<HTMLElement | null>(null);
const closeButtonRef = ref<HTMLButtonElement | null>(null);

const standardLinks = computed<readonly SidebarNavLink[]>(() => [
  { label: "Hem", to: "/", glyph: "home" },
  { label: "Katalog", to: "/browse", glyph: "choose-from-catalogue" },
  { label: "Mina filer", to: "/vault", glyph: "nav-files" },
  ...(props.canSeeContributor
    ? [{ label: "Mina verktyg", to: "/my-tools", glyph: "nav-my-tools" } as const]
    : []),
  { label: "Föreslå verktyg", to: "/suggestions/new", glyph: "nav-suggest-tool" },
  { label: "Profil", to: "/profile", glyph: "account-menu" },
]);

const adminLinks = computed<readonly SidebarNavLink[]>(() => [
  ...(props.canSeeAdmin
    ? [
        { label: "Hantera verktyg", to: "/admin/tools", glyph: "settings" } as const,
        { label: "Granska förslag", to: "/admin/suggestions", glyph: "nav-review-suggestions" } as const,
      ]
    : []),
  ...(props.canSeeSuperuser
    ? [{ label: "Användare", to: "/admin/users", glyph: "nav-users" } as const]
    : []),
]);

/** The close button and a selection dismiss the open drawer; the layout returns focus to Meny. */
function onDismiss(): void {
  if (props.isOpen) {
    emit("dismiss");
  }
}

function onLogout(): void {
  onDismiss();
  emit("logout");
}

function drawerFocusables(): HTMLElement[] {
  const nav = navRef.value;
  if (!nav) {
    return [];
  }
  return Array.from(nav.querySelectorAll<HTMLElement>("a[href], button:not([disabled])"));
}

/** Tab wraps between the drawer's first and last control. */
function containTab(event: KeyboardEvent): void {
  const focusables = drawerFocusables();
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  if (!first || !last) {
    return;
  }
  const active = document.activeElement;
  if (event.shiftKey && (active === first || !navRef.value?.contains(active))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (active === last || !navRef.value?.contains(active))) {
    event.preventDefault();
    first.focus();
  }
}

/**
 * Only the open phone drawer handles keys: Escape stops here so it closes the
 * drawer alone, and Tab stays inside. The inline sidebar and rail pass keys on.
 */
function onKeydown(event: KeyboardEvent): void {
  if (!props.isOpen) {
    return;
  }
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    emit("dismiss");
    return;
  }
  if (event.key === "Tab") {
    containTab(event);
  }
}

watch(
  () => props.isOpen,
  async (open) => {
    if (!open) {
      return;
    }
    await nextTick();
    closeButtonRef.value?.focus({ preventScroll: true });
  },
);
</script>

<template>
  <nav
    id="app-sidebar"
    ref="navRef"
    class="sidebar"
    :class="{ 'is-open': isOpen, 'is-rail': isRail }"
    aria-label="Huvudmeny"
    @keydown="onKeydown"
  >
    <div class="sidebar-head">
      <button
        ref="closeButtonRef"
        type="button"
        class="sidebar-close"
        aria-label="Stäng menyn"
        title="Stäng menyn"
        @click="onDismiss"
      >
        <UiGlyph
          meaning="close"
          :size="20"
        />
      </button>
    </div>

    <div class="sidebar-nav">
      <RouterLink
        v-for="link in standardLinks"
        :key="link.to"
        :to="link.to"
        class="sidebar-nav-item"
        :title="link.label"
        @click="onDismiss"
      >
        <UiGlyph
          :meaning="link.glyph"
          :size="20"
        />
        <span class="sidebar-nav-label">{{ link.label }}</span>
      </RouterLink>

      <template v-if="adminLinks.length > 0">
        <div class="sidebar-section">
          <span class="sidebar-nav-label">Administration</span>
        </div>
        <RouterLink
          v-for="link in adminLinks"
          :key="link.to"
          :to="link.to"
          class="sidebar-nav-item"
          :title="link.label"
          @click="onDismiss"
        >
          <UiGlyph
            :meaning="link.glyph"
            :size="20"
          />
          <span class="sidebar-nav-label">{{ link.label }}</span>
        </RouterLink>
      </template>
    </div>

    <!-- Phone drawer footer: the top-bar actions move here below 768 px. -->
    <div class="sidebar-footer">
      <span class="sidebar-user">{{ user?.email }}</span>
      <button
        type="button"
        class="sidebar-nav-item sidebar-help"
        aria-controls="help-panel"
        aria-haspopup="dialog"
        @click="emit('help')"
      >
        <UiGlyph
          meaning="help"
          :size="20"
        />
        <span class="sidebar-nav-label">Hjälp</span>
      </button>
      <button
        type="button"
        class="sidebar-nav-item sidebar-focus-toggle"
        :aria-pressed="isFocusMode"
        @click="emit('toggleFocusMode')"
      >
        <UiGlyph
          meaning="focus-mode"
          :size="20"
        />
        <span class="sidebar-nav-label">{{ isFocusMode ? "Avsluta fokusläge" : "Aktivera fokusläge" }}</span>
      </button>
      <button
        type="button"
        class="sidebar-nav-item sidebar-logout"
        :disabled="logoutInProgress"
        @click="onLogout"
      >
        <UiGlyph
          meaning="log-out"
          :size="20"
        />
        <span class="sidebar-nav-label">{{ logoutInProgress ? "Loggar ut…" : "Logga ut" }}</span>
      </button>
    </div>
  </nav>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--huleedu-space-1);
  min-height: 0;
  padding: var(--huleedu-space-3);
  overflow-y: auto;
  border-right: 1px solid var(--huleedu-surface-divider);
  background: var(--huleedu-canvas);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar-nav-item {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--huleedu-space-3);
  height: 40px;
  padding: 0 var(--huleedu-space-3);
  overflow: hidden;
  border: 0;
  border-radius: var(--huleedu-radius-md);
  background: transparent;
  color: var(--huleedu-navy-70);
  font-family: var(--huleedu-font-sans);
  font-size: var(--huleedu-text-sm);
  font-weight: var(--huleedu-font-medium);
  text-align: left;
  text-decoration: none;
  white-space: nowrap;
  cursor: pointer;
}

.sidebar-nav-item:focus-visible,
.sidebar-close:focus-visible {
  outline: 2px solid var(--huleedu-action-40);
  outline-offset: -2px;
}

.sidebar-nav-item[aria-current="page"] {
  background: var(--huleedu-action-10);
  box-shadow: inset 3px 0 0 var(--huleedu-action);
  color: var(--huleedu-navy);
}

.sidebar-nav-item[aria-current="page"] :deep(svg) {
  color: var(--huleedu-action);
}

.sidebar-nav-item:disabled {
  color: var(--huleedu-navy-40);
  cursor: not-allowed;
}

@media (hover: hover) {
  .sidebar-nav-item:not(:disabled):hover {
    background: var(--huleedu-action-05);
    color: var(--huleedu-navy);
  }

  .sidebar-nav-item[aria-current="page"]:hover {
    background: var(--huleedu-action-10);
  }
}

.sidebar-section {
  height: 16px;
  margin: var(--huleedu-space-4) var(--huleedu-space-3) var(--huleedu-space-1);
  color: var(--huleedu-navy-60);
  font-size: var(--huleedu-text-xs);
  font-weight: var(--huleedu-font-semibold);
  white-space: nowrap;
}

/* The drawer's head and footer exist only in the phone drawer. */
.sidebar-head,
.sidebar-footer {
  display: none;
}

/* Glyph rail: the desktop rail state and every tablet width. */
.sidebar.is-rail {
  padding: var(--huleedu-space-3) var(--huleedu-space-2-5);
}

.sidebar.is-rail .sidebar-nav-item {
  justify-content: center;
  padding: 0;
}

.sidebar.is-rail .sidebar-nav-label {
  display: none;
}

.sidebar.is-rail .sidebar-section {
  height: 1px;
  margin: var(--huleedu-space-3) var(--huleedu-space-2);
  background: var(--huleedu-surface-divider);
}

@media (max-width: 1279px) {
  .sidebar {
    padding: var(--huleedu-space-3) var(--huleedu-space-2-5);
  }

  .sidebar-nav-item {
    justify-content: center;
    padding: 0;
  }

  .sidebar-nav-label {
    display: none;
  }

  .sidebar-section {
    height: 1px;
    margin: var(--huleedu-space-3) var(--huleedu-space-2);
    background: var(--huleedu-surface-divider);
  }
}

/* Phone: a right-side drawer with labels, opened from Meny. */
@media (max-width: 767px) {
  .sidebar,
  .sidebar.is-rail {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 50;
    width: min(300px, 86vw);
    padding: var(--huleedu-space-3);
    border-right: 0;
    border-left: 1px solid var(--huleedu-panel-border);
    box-shadow: var(--huleedu-shadow-md);
    transform: translateX(100%);
    visibility: hidden;
    transition:
      transform 200ms ease-out,
      visibility 0s linear 200ms;
  }

  .sidebar.is-open {
    transform: none;
    visibility: visible;
    transition: transform 200ms ease-out;
  }

  .sidebar .sidebar-nav-item,
  .sidebar.is-rail .sidebar-nav-item {
    justify-content: flex-start;
    height: 44px;
    padding: 0 var(--huleedu-space-3);
  }

  .sidebar .sidebar-nav-label,
  .sidebar.is-rail .sidebar-nav-label {
    display: inline;
  }

  .sidebar .sidebar-section,
  .sidebar.is-rail .sidebar-section {
    height: 16px;
    margin: var(--huleedu-space-4) var(--huleedu-space-3) var(--huleedu-space-1);
    background: none;
  }

  .sidebar-head {
    display: flex;
    align-items: center;
    padding: 0 0 var(--huleedu-space-3) var(--huleedu-space-1);
  }

  .sidebar-footer {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-top: auto;
    padding-top: var(--huleedu-space-3);
    border-top: 1px solid var(--huleedu-surface-divider);
  }

  .sidebar-user {
    padding: 0 var(--huleedu-space-3) var(--huleedu-space-2);
    overflow-wrap: anywhere;
    color: var(--huleedu-navy-60);
    font-family: var(--huleedu-font-mono);
    font-size: var(--huleedu-text-xs);
  }
}

@media (max-width: 767px) and (prefers-reduced-motion: reduce) {
  .sidebar,
  .sidebar.is-rail,
  .sidebar.is-open {
    transition: none;
  }
}

.sidebar-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: var(--huleedu-radius-md);
  background: transparent;
  color: var(--huleedu-navy);
  cursor: pointer;
}

@media (hover: hover) {
  .sidebar-close:hover {
    background: var(--huleedu-action-05);
  }
}

.sidebar-focus-toggle[aria-pressed="true"] {
  color: var(--huleedu-action);
}
</style>
