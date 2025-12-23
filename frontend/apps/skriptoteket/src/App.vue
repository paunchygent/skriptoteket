<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useLoginModal } from "./composables/useLoginModal";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const loginModal = useLoginModal();

const logoutError = ref<string | null>(null);
const logoutInProgress = ref(false);

// Login modal form state
const email = ref("");
const password = ref("");
const submitError = ref<string | null>(null);
const isSubmitting = computed(() => auth.status === "loading");

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

const isHomePage = computed(() => route.name === "home");

function closeLoginModal() {
  loginModal.close();
  email.value = "";
  password.value = "";
  submitError.value = null;
}

async function onLoginSubmit(): Promise<void> {
  submitError.value = null;
  try {
    await auth.login({ email: email.value, password: password.value });
    const redirect = loginModal.redirectTo.value;
    closeLoginModal();
    if (redirect) {
      router.push(redirect);
    }
  } catch (error: unknown) {
    submitError.value = error instanceof Error ? error.message : "Inloggningen misslyckades";
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

          <button
            v-if="!isAuthenticated && !isHomePage"
            type="button"
            class="px-3 py-2 border border-navy bg-white shadow-brutal-sm font-semibold uppercase tracking-wide text-navy hover:bg-canvas"
            @click="loginModal.open()"
          >
            Logga in
          </button>
          <button
            v-if="isAuthenticated"
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

    <!-- Global Login Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="loginModal.isOpen.value"
          class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
          role="dialog"
          aria-modal="true"
          aria-labelledby="login-modal-title"
          :aria-describedby="submitError ? 'login-modal-error' : undefined"
          @click.self="closeLoginModal"
        >
          <div
            class="relative w-full max-w-sm mx-4 p-6 bg-canvas border border-navy shadow-brutal"
          >
            <button
              type="button"
              class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
              @click="closeLoginModal"
            >
              &times;
            </button>

            <h2
              id="login-modal-title"
              class="text-xl font-semibold text-navy"
            >
              Logga in
            </h2>

            <div
              v-if="submitError"
              id="login-modal-error"
              class="mt-4 p-3 border border-error bg-white text-error text-sm"
            >
              {{ submitError }}
            </div>

            <form class="mt-5 space-y-4" @submit.prevent="onLoginSubmit">
              <div>
                <label class="block text-sm font-semibold text-navy mb-1" for="modal-email">
                  E-post
                </label>
                <input
                  id="modal-email"
                  v-model="email"
                  type="email"
                  autocomplete="username"
                  required
                  class="w-full px-3 py-2 border border-navy bg-white text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <div>
                <label class="block text-sm font-semibold text-navy mb-1" for="modal-password">
                  Lösenord
                </label>
                <input
                  id="modal-password"
                  v-model="password"
                  type="password"
                  autocomplete="current-password"
                  required
                  class="w-full px-3 py-2 border border-navy bg-white text-navy"
                  :disabled="isSubmitting"
                >
              </div>

              <button
                type="submit"
                class="w-full px-4 py-2 bg-navy text-canvas border border-navy font-semibold uppercase tracking-wide hover:bg-burgundy transition-colors disabled:opacity-50"
                :disabled="isSubmitting"
              >
                {{ isSubmitting ? "Loggar in…" : "Logga in" }}
              </button>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
