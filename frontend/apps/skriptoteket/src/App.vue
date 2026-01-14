<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import LoginModal from "./components/auth/LoginModal.vue";
import HelpPanel from "./components/help/HelpPanel.vue";
import AuthLayout from "./components/layout/AuthLayout.vue";
import LandingLayout from "./components/layout/LandingLayout.vue";
import ToastHost from "./components/ui/ToastHost.vue";
import { useLoginModal } from "./composables/useLoginModal";
import { usePageTransition } from "./composables/usePageTransition";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const loginModal = useLoginModal();
const pageTransition = usePageTransition();

const logoutError = ref<string | null>(null);
const logoutInProgress = ref(false);

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

function closeLoginModal(): void {
  loginModal.close();
}

function onLoginSuccess(): void {
  const redirect = loginModal.redirectTo.value;
  closeLoginModal();
  if (redirect) {
    pageTransition.suppressNext();
    void router.push(redirect);
  }
}

watch(
  () => route.fullPath,
  async () => {
    if (!pageTransition.suppressNextPageTransition.value) {
      return;
    }
    await nextTick();
    pageTransition.reset();
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

    loginModal.open(route.fullPath);
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
        :class="{ 'route-stage--editor': isEditorRoute }"
      >
        <RouterView v-slot="{ Component, route: viewRoute }">
          <Transition
            v-if="isPageTransitionEnabled"
            name="page"
            mode="out-in"
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
      :can-see-contributor="canSeeContributor"
      :can-see-admin="canSeeAdmin"
      :can-see-superuser="canSeeSuperuser"
      :logout-error="logoutError"
      :logout-in-progress="logoutInProgress"
      @logout="onLogout"
    >
      <div
        class="route-stage"
        :class="{ 'route-stage--editor': isEditorRoute }"
      >
        <RouterView v-slot="{ Component, route: viewRoute }">
          <Transition
            v-if="isPageTransitionEnabled"
            name="page"
            mode="out-in"
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

    <HelpPanel />

    <ToastHost />

    <!-- Global Login Modal -->
    <LoginModal
      :is-open="loginModal.isOpen.value"
      @close="closeLoginModal"
      @success="onLoginSuccess"
    />
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}
</style>
