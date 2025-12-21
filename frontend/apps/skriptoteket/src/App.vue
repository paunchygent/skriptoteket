<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

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
    if (route.name === "login") {
      return;
    }

    await router.replace({
      name: "login",
      query: { next: route.fullPath },
    });
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
  <div style="padding: 16px">
    <header style="display: flex; gap: 12px; align-items: baseline">
      <h1 style="margin: 0">Skriptoteket SPA</h1>
      <nav style="display: flex; gap: 10px">
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/browse">Browse</RouterLink>
        <RouterLink
          v-if="canSeeContributor"
          to="/my-tools"
        >
          My tools
        </RouterLink>
        <RouterLink
          v-if="canSeeAdmin"
          to="/admin/tools"
        >
          Admin
        </RouterLink>

        <span
          v-if="isAuthenticated"
          style="margin-left: 12px; opacity: 0.8"
        >
          {{ auth.user?.email }} ({{ auth.user?.role }})
        </span>

        <RouterLink
          v-if="!isAuthenticated"
          to="/login"
          style="margin-left: 12px"
        >
          Login
        </RouterLink>
        <button
          v-else
          type="button"
          style="margin-left: 12px"
          @click="onLogout"
        >
          Logout
        </button>
      </nav>
    </header>
    <main style="margin-top: 16px">
      <p
        v-if="logoutError"
        style="margin: 0 0 12px; color: #b00020"
      >
        {{ logoutError }}
      </p>
      <RouterView />
    </main>
  </div>
</template>
