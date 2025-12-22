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
  <div class="min-h-screen bg-canvas text-navy">
    <header class="border-b border-navy bg-white shadow-brutal-sm">
      <div class="mx-auto max-w-5xl px-4 py-3 flex flex-wrap items-center justify-between gap-4">
        <div class="flex flex-wrap items-center gap-4">
          <RouterLink
            to="/"
            class="text-lg font-semibold text-navy hover:text-burgundy"
          >
            Skriptoteket
          </RouterLink>

          <nav class="flex flex-wrap items-center gap-3 text-sm">
            <RouterLink
              to="/"
              class="font-semibold uppercase tracking-wide text-navy/70 hover:text-burgundy"
            >
              Hem
            </RouterLink>
            <RouterLink
              to="/browse"
              class="font-semibold uppercase tracking-wide text-navy/70 hover:text-burgundy"
            >
              Katalog
            </RouterLink>
            <RouterLink
              v-if="isAuthenticated"
              to="/my-runs"
              class="font-semibold uppercase tracking-wide text-navy/70 hover:text-burgundy"
            >
              Mina körningar
            </RouterLink>
            <RouterLink
              v-if="canSeeContributor"
              to="/my-tools"
              class="font-semibold uppercase tracking-wide text-navy/70 hover:text-burgundy"
            >
              Mina verktyg
            </RouterLink>
            <RouterLink
              v-if="canSeeAdmin"
              to="/admin/tools"
              class="font-semibold uppercase tracking-wide text-navy/70 hover:text-burgundy"
            >
              Admin
            </RouterLink>
          </nav>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <span
            v-if="isAuthenticated"
            class="text-xs font-mono text-navy/60"
          >
            {{ auth.user?.email }} ({{ auth.user?.role }})
          </span>

          <RouterLink
            v-if="!isAuthenticated"
            to="/login"
            class="px-3 py-2 border border-navy bg-white shadow-brutal-sm font-semibold uppercase tracking-wide text-navy hover:bg-canvas"
          >
            Logga in
          </RouterLink>
          <button
            v-else
            type="button"
            class="px-3 py-2 border border-navy bg-white shadow-brutal-sm font-semibold uppercase tracking-wide text-navy hover:bg-canvas disabled:opacity-50"
            :disabled="logoutInProgress"
            @click="onLogout"
          >
            {{ logoutInProgress ? "Loggar ut…" : "Logga ut" }}
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-5xl px-4 py-6">
      <div
        v-if="logoutError"
        class="mb-4 p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
      >
        {{ logoutError }}
      </div>
      <RouterView />
    </main>
  </div>
</template>
