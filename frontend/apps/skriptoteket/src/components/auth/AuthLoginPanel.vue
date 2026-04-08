<script setup lang="ts">
/**
 * Page-based local login form panel.
 *
 * This component owns local-password sign-in, resend-verification recovery,
 * and the public forgot/register links used by the dedicated `/auth/login`
 * route. Redirect ownership stays with the parent auth-entry view so the route
 * contract remains the durable source of truth.
 */

import { computed, ref } from "vue";
import { useRoute } from "vue-router";

import { isApiError } from "../../api/client";
import {
  buildAuthContinuationApiPayload,
  buildAuthContinuationLocation,
  readAuthContinuation,
} from "../../composables/auth/authEntryNavigation";
import { useVerificationResend } from "../../composables/auth/useVerificationResend";
import { useAuthStore } from "../../stores/auth";
import SystemMessage from "../ui/SystemMessage.vue";

const emit = defineEmits<{
  success: [];
}>();

const auth = useAuthStore();
const route = useRoute();

const email = ref("");
const password = ref("");
const submitError = ref<string | null>(null);
const showVerificationResend = ref(false);
const isSubmitting = computed(() => auth.status === "loading");
const continuation = computed(() => readAuthContinuation(route.query, window.history.state));
const forgotPasswordLocation = computed(() =>
  buildAuthContinuationLocation({ name: "forgot-password" }, continuation.value),
);
const registerLocation = computed(() =>
  buildAuthContinuationLocation({ name: "register" }, continuation.value),
);
const {
  clearMessages: clearVerificationMessages,
  errorMessage: verificationErrorMessage,
  isSubmitting: isVerificationSubmitting,
  resend: resendVerificationEmail,
  successMessage: verificationSuccessMessage,
} = useVerificationResend();

async function onSubmit(): Promise<void> {
  submitError.value = null;
  showVerificationResend.value = false;
  clearVerificationMessages();

  try {
    await auth.login({ email: email.value, password: password.value });
    emit("success");
  } catch (error: unknown) {
    if (isApiError(error) && error.code === "EMAIL_NOT_VERIFIED") {
      showVerificationResend.value = true;
    }

    submitError.value =
      error instanceof Error ? error.message : "Inloggningen misslyckades";
  }
}

async function resendVerification(): Promise<void> {
  await resendVerificationEmail(email.value, buildAuthContinuationApiPayload(continuation.value));
}
</script>

<template>
  <div class="border border-navy bg-canvas p-6 shadow-brutal md:p-8">
    <SystemMessage
      id="auth-login-error"
      v-model="submitError"
      variant="error"
    />
    <SystemMessage
      v-model="verificationErrorMessage"
      class="mt-4"
      variant="error"
    />
    <SystemMessage
      v-model="verificationSuccessMessage"
      class="mt-4"
      variant="success"
      :dismissible="false"
    />

    <form
      class="mt-5 space-y-4"
      @submit.prevent="onSubmit"
    >
      <div>
        <label
          class="mb-1 block text-xs font-semibold tracking-wide text-navy/70 uppercase"
          for="auth-login-email"
        >
          E-post
        </label>
        <input
          id="auth-login-email"
          v-model="email"
          type="email"
          autocomplete="username"
          required
          class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
          :disabled="isSubmitting"
        >
      </div>

      <div>
        <label
          class="mb-1 block text-xs font-semibold tracking-wide text-navy/70 uppercase"
          for="auth-login-password"
        >
          Lösenord
        </label>
        <input
          id="auth-login-password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
          :disabled="isSubmitting"
        >
      </div>

      <button
        type="submit"
        class="btn-primary w-full"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? "Loggar in…" : "Logga in" }}
      </button>
    </form>

    <div
      v-if="showVerificationResend"
      class="mt-4 space-y-3 border border-navy bg-white p-4 shadow-brutal-sm"
    >
      <p class="text-sm text-navy/70">
        Behöver du ett nytt verifieringsmejl till den här adressen?
      </p>
      <button
        type="button"
        class="btn-secondary w-full"
        :disabled="isVerificationSubmitting"
        @click="resendVerification"
      >
        {{
          isVerificationSubmitting
            ? "Skickar verifieringsmejl…"
            : "Skicka nytt verifieringsmejl"
        }}
      </button>
      <p class="text-xs text-navy/60">
        Kontrollera även skräppost om inget mejl från `noreply@hule.education` syns i inkorgen.
      </p>
    </div>

    <p class="mt-4 text-xs text-navy/70">
      <RouterLink
        :to="forgotPasswordLocation"
        class="text-navy underline hover:text-burgundy"
      >
        Glömt lösenord?
      </RouterLink>
    </p>

    <p class="mt-3 text-xs text-navy/70">
      Inget konto?
      <RouterLink
        :to="registerLocation"
        class="text-navy underline hover:text-burgundy"
      >
        Skapa konto
      </RouterLink>
    </p>
  </div>
</template>
