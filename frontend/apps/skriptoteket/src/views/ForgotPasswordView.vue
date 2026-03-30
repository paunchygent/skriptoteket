<script setup lang="ts">
/**
 * Unauthenticated password-reset request screen.
 *
 * This view exposes the public forgot-password flow while keeping the backend
 * authoritative for eligibility, throttling, and generic success semantics.
 */

import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiPost } from "../api/client";
import SystemMessage from "../components/ui/SystemMessage.vue";
import { useVerificationResend } from "../composables/auth/useVerificationResend";
import { useAuthStore } from "../stores/auth";

type ForgotPasswordResponse = {
  message: string;
};

const auth = useAuthStore();
const router = useRouter();

const email = ref("");
const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);
const hasSubmittedReset = ref(false);

const {
  canResend: canResendVerification,
  clearMessages: clearVerificationMessages,
  cooldownRemainingSeconds: verificationCooldownRemainingSeconds,
  errorMessage: verificationErrorMessage,
  isSubmitting: isVerificationSubmitting,
  resend: resendVerificationEmail,
  successMessage: verificationSuccessMessage,
} = useVerificationResend();

const canOfferVerificationResend = computed(() => hasSubmittedReset.value && email.value.trim() !== "");

onMounted(async () => {
  await auth.bootstrap();
  if (auth.isAuthenticated) {
    await router.replace("/");
  }
});

async function submit(): Promise<void> {
  if (isSubmitting.value) {
    return;
  }

  const normalizedEmail = email.value.trim();
  if (!normalizedEmail) {
    errorMessage.value = "Ange din e-postadress.";
    return;
  }

  errorMessage.value = null;
  successMessage.value = null;
  clearVerificationMessages();
  isSubmitting.value = true;

  try {
    const response = await apiPost<ForgotPasswordResponse>("/api/v1/auth/forgot-password", {
      email: normalizedEmail,
    });
    successMessage.value = response.message;
    hasSubmittedReset.value = true;
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof Error ? error.message : "Det gick inte att begära en återställningslänk.";
  } finally {
    isSubmitting.value = false;
  }
}

async function resendVerification(): Promise<void> {
  await resendVerificationEmail(email.value);
}
</script>

<template>
  <div class="max-w-xl mx-auto space-y-6">
    <header class="space-y-2">
      <h1 class="page-title">Glömt lösenord</h1>
      <p class="page-description">
        Ange din e-postadress så försöker vi skicka en återställningslänk om kontot kan
        återställas.
      </p>
    </header>

    <SystemMessage
      v-model="errorMessage"
      variant="error"
    />
    <SystemMessage
      v-model="successMessage"
      variant="success"
      :dismissible="false"
    />
    <SystemMessage
      v-model="verificationErrorMessage"
      variant="error"
    />
    <SystemMessage
      v-model="verificationSuccessMessage"
      variant="success"
      :dismissible="false"
    />

    <form
      class="space-y-4"
      @submit.prevent="submit"
    >
      <div class="space-y-2">
        <label
          for="forgot-password-email"
          class="text-sm font-semibold text-navy"
        >E-post</label>
        <input
          id="forgot-password-email"
          v-model="email"
          type="email"
          required
          autocomplete="username"
          class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
          :disabled="isSubmitting"
        >
      </div>

      <button
        type="submit"
        class="btn-cta w-full"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? "Skickar återställningslänk…" : "Skicka återställningslänk" }}
      </button>
    </form>

    <p class="text-sm text-navy/70">
      Kom du på lösenordet?
      <RouterLink
        to="/login"
        class="text-navy underline hover:text-burgundy"
      >
        Logga in
      </RouterLink>
    </p>

    <section
      v-if="canOfferVerificationResend"
      class="space-y-3 border border-navy bg-canvas px-4 py-4 shadow-brutal-sm"
    >
      <h2 class="text-sm font-semibold uppercase tracking-wide text-navy">
        Inte verifierat än?
      </h2>
      <p class="text-sm text-navy/70">
        Om kontot ännu inte är verifierat kan du be om ett nytt verifieringsmejl till samma
        adress.
      </p>
      <button
        type="button"
        class="btn-secondary w-full"
        :disabled="!canResendVerification"
        @click="resendVerification"
      >
        {{
          isVerificationSubmitting
            ? "Skickar verifieringsmejl…"
            : verificationCooldownRemainingSeconds > 0
              ? `Försök igen om ${verificationCooldownRemainingSeconds}s`
              : "Skicka nytt verifieringsmejl"
        }}
      </button>
      <p class="text-xs text-navy/60">
        Kontrollera också skräppost om inget mejl från `noreply@hule.education` syns i inkorgen.
      </p>
    </section>
  </div>
</template>
