<script setup lang="ts">
/**
 * Signed-in app shell: top bar, sidebar and page frame.
 *
 * Relationships:
 * - one CSS grid owns the shell geometry at every width: desktop (>= 1280 px)
 *   shows the 240 px sidebar or the 64 px rail, tablet always the rail, phone
 *   (< 768 px) a single column with the navigation in a Meny drawer
 * - owns the drawer state; while the phone drawer is open the top bar and the
 *   page are inert, so only the drawer takes focus and pointer input
 * - reads focus mode and the rail state from the
 *   per-user layout store; focus mode hides the sidebar at 768 px and wider and
 *   keeps the top bar
 * - selected game routes switch to an immersive mode with only the dark top bar
 * - the page frame pads every route and centres ordinary routes in a 1040 px
 *   column; the editor and Klassrumskartan get a
 *   flex-column frame they fill, and the exam workspace (TASK-SKRIPT-40-04-03)
 *   and immersive routes get an unpadded, non-scrolling frame
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, watchEffect } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";

import AuthSidebar from "./AuthSidebar.vue";
import AuthTopBar from "./AuthTopBar.vue";
import { useHelp } from "../help/useHelp";
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
const { focusMode, sidebarCollapsed } = storeToRefs(layout);
const { open: openHelp } = useHelp();
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
const isExamWorkspaceRoute = computed(() => route.name === "exam-workspace");
/** Ordinary routes sit in the centred page column; the others fill the frame. */
const isPageRoute = computed(
  () =>
    !isEditorRoute.value
    && !isClassroomPlannerRoute.value
    && !isExamWorkspaceRoute.value
    && !isImmersiveCuratedAppRoute.value,
);

const sidebarOpen = ref(false);
/** `undefined` removes the attribute; `inert="false"` would still be inert. */
const drawerInert = computed(() => (sidebarOpen.value ? true : undefined));
const topBarRef = ref<InstanceType<typeof AuthTopBar> | null>(null);

function menuButton(): HTMLElement | null {
  return topBarRef.value?.menuButtonElement() ?? null;
}

/** Waits for the render that lifts `inert` from the top bar before focusing Meny. */
async function returnFocusToMenu(): Promise<void> {
  await nextTick();
  menuButton()?.focus({ preventScroll: true });
}

function toggleSidebar(): void {
  sidebarOpen.value = !sidebarOpen.value;
}

function closeSidebar(): void {
  sidebarOpen.value = false;
}

/** Escape, the close button and the backdrop dismiss the drawer back to Meny. */
function dismissSidebar(): void {
  closeSidebar();
  void returnFocusToMenu();
}

function onLogout(): void {
  emit("logout");
}

/**
 * Drawer help hands the Meny button to the shared help panel as its opener, so
 * closing help returns focus to the drawer trigger while the drawer stays shut.
 */
function onDrawerHelp(): void {
  closeSidebar();
  openHelp(menuButton());
}

/**
 * Drawer focus mode closes the drawer and returns focus to the visible Meny
 * button, because the drawer control is no longer reachable once it closes.
 */
function onDrawerToggleFocusMode(): void {
  closeSidebar();
  layout.toggle();
  void returnFocusToMenu();
}

/** The drawer exists only below 768 px; widening the window closes it. */
const PHONE_QUERY = "(max-width: 767px)";
let phoneMedia: MediaQueryList | null = null;

function onPhoneMediaChange(event: MediaQueryListEvent): void {
  if (!event.matches) {
    closeSidebar();
  }
}

onMounted(() => {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return;
  }
  phoneMedia = window.matchMedia(PHONE_QUERY);
  phoneMedia.addEventListener("change", onPhoneMediaChange);
});

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
  phoneMedia?.removeEventListener("change", onPhoneMediaChange);
  if (typeof document !== "undefined") {
    document.body.classList.remove("app-shell-game-mode");
  }
});
</script>

<template>
  <div
    class="auth-shell"
    :class="{
      'is-rail': sidebarCollapsed,
      'is-focus-mode': focusMode,
      'is-immersive-route': isImmersiveCuratedAppRoute,
    }"
  >
    <AuthTopBar
      ref="topBarRef"
      :inert="drawerInert"
      :logout-in-progress="logoutInProgress"
      :is-focus-mode="focusMode"
      :is-sidebar-collapsed="sidebarCollapsed"
      :is-immersive-route="isImmersiveCuratedAppRoute"
      :is-menu-open="sidebarOpen"
      @toggle-focus-mode="layout.toggle()"
      @toggle-sidebar="layout.toggleSidebarCollapsed()"
      @toggle-menu="toggleSidebar"
      @logout="onLogout"
    />

    <AuthSidebar
      v-if="!isImmersiveCuratedAppRoute"
      :is-open="sidebarOpen"
      :is-rail="sidebarCollapsed"
      :is-focus-mode="focusMode"
      :user="user"
      :can-see-contributor="canSeeContributor"
      :can-see-admin="canSeeAdmin"
      :can-see-superuser="canSeeSuperuser"
      :logout-in-progress="logoutInProgress"
      @dismiss="dismissSidebar"
      @help="onDrawerHelp"
      @logout="onLogout"
      @toggle-focus-mode="onDrawerToggleFocusMode"
    />

    <div
      v-if="sidebarOpen && !isImmersiveCuratedAppRoute"
      class="auth-nav-backdrop"
      aria-hidden="true"
      @click="dismissSidebar"
    />

    <main
      class="auth-main-content"
      :inert="drawerInert"
      :class="{
        'auth-main-content--page': isPageRoute,
        'auth-main-content--editor': isEditorRoute,
        'auth-main-content--workspace': isClassroomPlannerRoute,
        'auth-main-content--exam-workspace': isExamWorkspaceRoute,
        'auth-main-content--immersive': isImmersiveCuratedAppRoute,
      }"
    >
      <slot />
    </main>
  </div>
</template>

<style scoped>
/* Shell grid: the only owner of the shell's height and column geometry. */
.auth-shell {
  --shell-top: 56px;
  --shell-side: var(--huleedu-sidebar-width);
  --shell-rail: 64px;
  /* Width of the sidebar outside focus mode; main.css expand-left-* reads it
     so focus mode widens panels by exactly the space the sidebar gave up. */
  --shell-sidebar-inline: var(--shell-side);

  display: grid;
  grid-template-rows: var(--shell-top) minmax(0, 1fr);
  grid-template-columns: var(--shell-side) minmax(0, 1fr);
  grid-template-areas:
    "top top"
    "side main";
  height: 100vh;
  height: 100dvh;
  overflow: hidden;
}

.auth-shell.is-rail {
  --shell-sidebar-inline: var(--shell-rail);

  grid-template-columns: var(--shell-rail) minmax(0, 1fr);
}

@media (max-width: 1279px) {
  .auth-shell {
    --shell-sidebar-inline: var(--shell-rail);

    grid-template-columns: var(--shell-rail) minmax(0, 1fr);
  }
}

.auth-shell.is-focus-mode,
.auth-shell.is-immersive-route {
  grid-template-columns: minmax(0, 1fr);
  grid-template-areas:
    "top"
    "main";
}

.auth-shell.is-focus-mode > .sidebar {
  display: none;
}

@media (max-width: 767px) {
  .auth-shell,
  .auth-shell.is-rail {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas:
      "top"
      "main";
  }

  /* The phone drawer carries the way out of focus mode, so it stays. */
  .auth-shell.is-focus-mode > .sidebar {
    display: flex;
  }
}

.auth-shell > .topbar {
  grid-area: top;
  z-index: 20;
}

.auth-shell > .sidebar {
  grid-area: side;
}

.auth-nav-backdrop {
  display: none;
}

@media (max-width: 767px) {
  .auth-nav-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 49;
    background: var(--huleedu-navy-30);
  }
}

/* Page frame: a plain canvas surface over the global grid paper; ordinary
   routes sit in a centred 1040 px column that focus mode widens by the width
   the sidebar gave up, so the column's right edge holds still. */
.auth-main-content {
  grid-area: main;
  min-width: 0;
  min-height: 0;
  padding: var(--huleedu-space-5) var(--huleedu-space-4);
  overflow-y: auto;
  scrollbar-gutter: stable;
  background: var(--huleedu-canvas);
}

@media (min-width: 768px) {
  .auth-main-content {
    padding: var(--huleedu-space-8);
  }
}

.auth-main-content--page :deep(.route-stage) {
  max-width: 1040px;
  margin-inline: auto;
}

.auth-shell.is-focus-mode .auth-main-content--page :deep(.route-stage) {
  max-width: calc(1040px + var(--shell-sidebar-inline));
}

/* Flex-column frames that their route fills. */
.auth-main-content--editor,
.auth-main-content--workspace,
.auth-main-content--exam-workspace,
.auth-main-content--immersive {
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

.auth-main-content--editor :deep(.route-stage),
.auth-main-content--editor :deep(.route-stage-item),
.auth-main-content--workspace :deep(.route-stage),
.auth-main-content--workspace :deep(.route-stage-item),
.auth-main-content--exam-workspace :deep(.route-stage),
.auth-main-content--exam-workspace :deep(.route-stage-item),
.auth-main-content--immersive :deep(.route-stage),
.auth-main-content--immersive :deep(.route-stage-item) {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
}

@media (min-width: 1024px) {
  .auth-main-content--editor {
    overflow: hidden;
  }
}

.auth-main-content--exam-workspace,
.auth-main-content--immersive {
  padding: 0;
  overflow: hidden;
  scrollbar-gutter: auto;
}
</style>
