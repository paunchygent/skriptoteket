<script setup lang="ts">
/**
 * Dedicated auth-entry page.
 *
 * This view owns the HuleEdu sign-in handoff used by signed-out entry
 * surfaces and protected-route interruptions.
 */

import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import AuthLoginPanel from "../components/auth/AuthLoginPanel.vue";
import {
  AUTH_LOGIN_ROUTE_NAME,
  readAuthContinuation,
  resolveAuthLoginSuccessLocation,
} from "../composables/auth/authEntryNavigation";
import { usePageTransition } from "../composables/usePageTransition";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const pageTransition = usePageTransition();
const isCompletingLogin = ref(false);

const continuation = computed(() => readAuthContinuation(route.query, window.history.state));
const redirectCopy = computed(() => {
  if (continuation.value.nextPath) {
    return "Efter inloggning skickas du vidare till rätt sida i Skriptoteket.";
  }

  return "Logga in för att fortsätta till din startsida i Skriptoteket.";
});

async function completeAuthEntry(): Promise<void> {
  if (isCompletingLogin.value) {
    return;
  }

  isCompletingLogin.value = true;
  pageTransition.suppressNext();

  try {
    await router.push(resolveAuthLoginSuccessLocation(continuation.value, window.history.state));
  } finally {
    isCompletingLogin.value = false;
  }
}

watch(
  () => auth.isAuthenticated,
  (value) => {
    if (!value || route.name !== AUTH_LOGIN_ROUTE_NAME) {
      return;
    }

    void completeAuthEntry();
  },
  { immediate: true },
);
</script>

<template>
  <div class="flex min-h-[60vh] items-center justify-center px-4 py-10">
    <section class="w-full max-w-md space-y-5">
      <header class="space-y-3 text-center">
        <p class="text-xs font-semibold tracking-[var(--huleedu-tracking-label)] text-navy/60 uppercase">
          Skriptoteket
        </p>
        <h1 class="font-serif text-4xl font-semibold tracking-[-0.03em] text-navy">
          Logga in
        </h1>
        <p class="text-sm leading-6 text-navy/70">
          {{ redirectCopy }}
        </p>
      </header>

      <AuthLoginPanel />
    </section>
  </div>
</template>
