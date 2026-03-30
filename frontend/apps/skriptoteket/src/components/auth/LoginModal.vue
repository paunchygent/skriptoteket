<script setup lang="ts">
import { computed, ref } from "vue";

import { isApiError } from "../../api/client";
import { useVerificationResend } from "../../composables/auth/useVerificationResend";
import SystemMessage from "../ui/SystemMessage.vue";
import { useAuthStore } from "../../stores/auth";

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  close: [];
  success: [];
}>();

const auth = useAuthStore();

const email = ref("");
const password = ref("");
const submitError = ref<string | null>(null);
const showVerificationResend = ref(false);
const isSubmitting = computed(() => auth.status === "loading");
const {
  canResend: canResendVerification,
  clearMessages: clearVerificationMessages,
  cooldownRemainingSeconds: verificationCooldownRemainingSeconds,
  errorMessage: verificationErrorMessage,
  isSubmitting: isVerificationSubmitting,
  resend: resendVerificationEmail,
  successMessage: verificationSuccessMessage,
} = useVerificationResend();

function closeModal(): void {
  email.value = "";
  password.value = "";
  submitError.value = null;
  showVerificationResend.value = false;
  clearVerificationMessages();
  emit("close");
}

async function onSubmit(): Promise<void> {
  submitError.value = null;
  showVerificationResend.value = false;
  clearVerificationMessages();
  try {
    await auth.login({ email: email.value, password: password.value });
    emit("success");
    closeModal();
  } catch (error: unknown) {
    if (isApiError(error) && error.code === "EMAIL_NOT_VERIFIED") {
      showVerificationResend.value = true;
    }
    submitError.value =
      error instanceof Error ? error.message : "Inloggningen misslyckades";
  }
}

async function resendVerification(): Promise<void> {
  await resendVerificationEmail(email.value);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="props.isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-modal-title"
        :aria-describedby="submitError ? 'login-modal-error' : undefined"
        @click.self="closeModal"
      >
        <div
          class="relative w-full max-w-sm mx-4 p-6 bg-canvas border border-navy shadow-brutal"
        >
          <button
            type="button"
            class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
            @click="closeModal"
          >
            &times;
          </button>

          <h2
            id="login-modal-title"
            class="text-xl font-semibold text-navy"
          >
            Logga in
          </h2>

          <SystemMessage
            id="login-modal-error"
            v-model="submitError"
            class="mt-4"
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
                class="block text-xs font-semibold uppercase tracking-wide text-navy/70 mb-1"
                for="modal-email"
              >
                E-post
              </label>
              <input
                id="modal-email"
                v-model="email"
                type="email"
                autocomplete="username"
                required
                class="w-full px-3 py-2 border border-navy bg-white text-sm text-navy shadow-brutal-sm"
                :disabled="isSubmitting"
              >
            </div>

            <div>
              <label
                class="block text-xs font-semibold uppercase tracking-wide text-navy/70 mb-1"
                for="modal-password"
              >
                Lösenord
              </label>
              <input
                id="modal-password"
                v-model="password"
                type="password"
                autocomplete="current-password"
                required
                class="w-full px-3 py-2 border border-navy bg-white text-sm text-navy shadow-brutal-sm"
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
              Kontrollera även skräppost om inget mejl från `noreply@hule.education` syns i
              inkorgen.
            </p>
          </div>

          <p class="mt-4 text-xs text-navy/70">
            <RouterLink
              to="/forgot-password"
              class="text-navy underline hover:text-burgundy"
              @click="closeModal"
            >
              Glömt lösenord?
            </RouterLink>
          </p>

          <p class="mt-3 text-xs text-navy/70">
            Inget konto?
            <RouterLink
              to="/register"
              class="text-navy underline hover:text-burgundy"
              @click="closeModal"
            >
              Skapa konto
            </RouterLink>
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
