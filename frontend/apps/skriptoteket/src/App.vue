<script setup lang="ts">
/**
 * Root SPA shell.
 *
 * This component hosts the global layouts and auth-reactive route recovery so
 * protected curated-app routes keep their entry contracts intact through the
 * dedicated `/auth/login` page contract.
 */

import { computed, defineAsyncComponent, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import AuthLayout from "./components/layout/AuthLayout.vue";
import LandingLayout from "./components/layout/LandingLayout.vue";
import ToastHost from "./components/ui/ToastHost.vue";
import {
  buildProtectedAuthEntryLocationFromCurrentRoute,
} from "./composables/auth/authEntryNavigation";
import { usePageTransition } from "./composables/usePageTransition";
import { useAuthStore } from "./stores/auth";
import { useHelp } from "./components/help/useHelp";
import { CLASSROOM_PLANNER_APP_ID } from "./views/apps/classroomPlannerNavigation";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const help = useHelp();
const pageTransition = usePageTransition();

const logoutError = ref<string | null>(null);
const logoutInProgress = ref(false);
const helpPanelEnabled = ref(false);

const HelpPanel = defineAsyncComponent(() => import("./components/help/HelpPanel.vue"));

if (help.isOpen.value) {
  helpPanelEnabled.value = true;
}

const isAuthenticated = computed(() => auth.isAuthenticated);
const canSeeContributor = computed(() => auth.hasAtLeastRole("contributor"));
const canSeeAdmin = computed(() => auth.hasAtLeastRole("admin"));
const canSeeSuperuser = computed(() => auth.hasAtLeastRole("superuser"));

const isPageTransitionEnabled = computed(() => {
  if (pageTransition.suppressNextPageTransition.value) {
    return false;
  }
  return route.meta.pageTransition !== false && !route.redirectedFrom;
});

const isEditorRoute = computed(
  () => route.name === "admin-tool-editor" || route.name === "admin-tool-version-editor",
);

const isClassroomPlannerRoute = computed(() => {
  const appId = route.params?.appId;
  return (
    (route.name === "app-detail" || route.name === "public-app-detail")
    && appId === CLASSROOM_PLANNER_APP_ID
  );
});

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

watch(
  () => route.fullPath,
  async () => {
    if (pageTransition.suppressNextPageTransition.value) {
      await nextTick();
      pageTransition.reset();
    }
  },
  { flush: "post" },
);

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

    pageTransition.suppressNext();
    void router.push(
      buildProtectedAuthEntryLocationFromCurrentRoute(route, window.history.state),
    );
  },
);

watch(
  () => help.isOpen.value,
  (open) => {
    if (open) {
      helpPanelEnabled.value = true;
    }
  },
);

async function onLogout(): Promise<void> {
  logoutError.value = null;
  logoutInProgress.value = true;

  try {
    await auth.logout();
    pageTransition.suppressNext();
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
    <!-- Unauthenticated: Landing layout -->
    <LandingLayout v-if="!isAuthenticated">
      <div
        class="route-stage"
        :class="{
          'route-stage--editor': isEditorRoute,
          'route-stage--workspace': isClassroomPlannerRoute,
        }"
      >
        <RouterView v-slot="{ Component, route: viewRoute }">
          <Transition
            v-if="isPageTransitionEnabled"
            name="page"
            :duration="150"
          >
            <div
              :key="viewRoute.path"
              class="route-stage-item"
            >
              <component :is="Component" />
            </div>
          </Transition>
          <div
            v-else
            :key="viewRoute.path"
            class="route-stage-item"
          >
            <component :is="Component" />
          </div>
        </RouterView>
      </div>
    </LandingLayout>

    <!-- Authenticated: Sidebar + Top bar layout -->
    <AuthLayout
      v-else
      :user="auth.user"
      :profile="auth.profile"
      :ai-policy="auth.aiPolicy"
      :can-see-contributor="canSeeContributor"
      :can-see-admin="canSeeAdmin"
      :can-see-superuser="canSeeSuperuser"
      :logout-error="logoutError"
      :logout-in-progress="logoutInProgress"
      @logout="onLogout"
    >
      <div
        class="route-stage"
        :class="{
          'route-stage--editor': isEditorRoute,
          'route-stage--workspace': isClassroomPlannerRoute,
        }"
      >
        <RouterView v-slot="{ Component, route: viewRoute }">
          <Transition
            v-if="isPageTransitionEnabled"
            name="page"
            :duration="150"
          >
            <div
              :key="viewRoute.path"
              class="route-stage-item"
            >
              <component :is="Component" />
            </div>
          </Transition>
          <div
            v-else
            :key="viewRoute.path"
            class="route-stage-item"
          >
            <component :is="Component" />
          </div>
        </RouterView>
      </div>
    </AuthLayout>

    <HelpPanel v-if="helpPanelEnabled" />

    <ToastHost />
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}
</style>
