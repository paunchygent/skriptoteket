<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import LoginModal from "./components/auth/LoginModal.vue";
import HelpPanel from "./components/help/HelpPanel.vue";
import AuthLayout from "./components/layout/AuthLayout.vue";
import LandingLayout from "./components/layout/LandingLayout.vue";
import ToastHost from "./components/ui/ToastHost.vue";
import { useLoginModal } from "./composables/useLoginModal";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const loginModal = useLoginModal();

const logoutError = ref<string | null>(null);
const logoutInProgress = ref(false);

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

function closeLoginModal(): void {
  loginModal.close();
}

function onLoginSuccess(): void {
  const redirect = loginModal.redirectTo.value;
  closeLoginModal();
  if (redirect) {
    router.push(redirect);
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

    loginModal.open(route.fullPath);
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
    <!-- Unauthenticated: Landing layout -->
    <LandingLayout v-if="!isAuthenticated">
      <RouterView />
    </LandingLayout>

    <!-- Authenticated: Sidebar + Top bar layout -->
    <AuthLayout
      v-else
      :user="auth.user"
      :can-see-contributor="canSeeContributor"
      :can-see-admin="canSeeAdmin"
      :logout-error="logoutError"
      :logout-in-progress="logoutInProgress"
      @logout="onLogout"
    >
      <RouterView />
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
