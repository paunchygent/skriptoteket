<script setup lang="ts">
/**
 * Dedicated auth-entry page.
 *
 * This view owns the HuleEdu sign-in handoff used by signed-out entry
 * surfaces and protected-route interruptions.
 */

import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { sharedAuthCeremonyUrl } from "../api/sharedAuth";
import AuthLoginPanel from "../components/auth/AuthLoginPanel.vue";
import {
  clearAuthCallbackRetry,
  hasAuthCallbackRetry,
  rememberAuthCallbackRetry,
} from "../composables/auth/authCallbackRetry";
import {
  AUTH_CALLBACK_PATH,
  AUTH_LOGIN_PATH,
  isAuthEntryPath,
  readAuthContinuation,
  resolveAuthLoginSuccessLocation,
} from "../composables/auth/authEntryNavigation";
import { redirectToSharedAuthCeremony } from "../composables/auth/sharedAuthRedirect";
import { usePageTransition } from "../composables/usePageTransition";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const pageTransition = usePageTransition();
const isCompletingLogin = ref(false);
const hasStartedLoginHandoff = ref(false);

const continuation = computed(() => readAuthContinuation(route.query, window.history.state));
const loginUrl = computed(() =>
  sharedAuthCeremonyUrl({
    nextPath: continuation.value.nextPath,
    origin: window.location.origin,
  }),
);
const isAnonymousCallback = computed(
  () => route.path === AUTH_CALLBACK_PATH && !auth.isAuthenticated,
);
const isCallbackRecovery = computed(
  () => isAnonymousCallback.value && hasAuthCallbackRetry(continuation.value.nextPath),
);
const redirectCopy = computed(() => {
  if (isCallbackRecovery.value) {
    return "Inloggningen slutfördes inte. Logga in igen för att fortsätta.";
  }

  if (isAnonymousCallback.value) {
    return "Vi försöker öppna inloggningen igen.";
  }

  if (route.path === AUTH_LOGIN_PATH && !auth.isAuthenticated) {
    return "Inloggningen öppnas automatiskt.";
  }

  if (continuation.value.nextPath) {
    return "Efter inloggning skickas du vidare till rätt sida i Skriptoteket.";
  }

  return "Logga in för att fortsätta till din startsida i Skriptoteket.";
});
const panelIntroCopy = computed(() =>
  isCallbackRecovery.value
    ? "Inloggningen blev inte klar. Logga in igen för att fortsätta."
    : "Om inloggningen inte öppnas automatiskt kan du öppna den igen här.",
);
const primaryActionLabel = computed(() =>
  isCallbackRecovery.value ? "Logga in igen" : "Öppna inloggningen",
);
const showAccountLinks = computed(() => !isCallbackRecovery.value);

async function completeAuthEntry(): Promise<void> {
  if (isCompletingLogin.value) {
    return;
  }

  isCompletingLogin.value = true;
  pageTransition.suppressNext();

  try {
    clearAuthCallbackRetry(continuation.value.nextPath);
    await router.push(resolveAuthLoginSuccessLocation(continuation.value, window.history.state));
  } finally {
    isCompletingLogin.value = false;
  }
}

function startSharedLoginHandoff(): void {
  const shouldStartLoginHandoff = route.path === AUTH_LOGIN_PATH;
  const shouldRetryAnonymousCallback =
    isAnonymousCallback.value && !hasAuthCallbackRetry(continuation.value.nextPath);

  if (
    hasStartedLoginHandoff.value ||
    auth.isAuthenticated ||
    (!shouldStartLoginHandoff && !shouldRetryAnonymousCallback)
  ) {
    return;
  }

  hasStartedLoginHandoff.value = true;
  if (shouldRetryAnonymousCallback) {
    rememberAuthCallbackRetry(continuation.value.nextPath);
  }
  pageTransition.suppressNext();
  redirectToSharedAuthCeremony(loginUrl.value);
}

watch(
  () => [auth.isAuthenticated, route.path, loginUrl.value] as const,
  (value) => {
    if (value[0] && isAuthEntryPath(route.path)) {
      void completeAuthEntry();
      return;
    }

    startSharedLoginHandoff();
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

      <AuthLoginPanel
        :intro-copy="panelIntroCopy"
        :primary-label="primaryActionLabel"
        :show-account-links="showAccountLinks"
      />
    </section>
  </div>
</template>
