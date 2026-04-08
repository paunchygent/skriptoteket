<script setup lang="ts">
/**
 * Password-reset execution screen for emailed reset links.
 *
 * This view reads the token from the query string, submits the new password to
 * the backend, and keeps success/failure rendering aligned with the documented
 * public API contract.
 */

import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { ApiError, apiPost, isApiError } from "../api/client";
import { IconCheck, IconWarning, IconX } from "../components/icons";
import SystemMessage from "../components/ui/SystemMessage.vue";
import {
  buildAuthContinuationLocation,
  buildSignedOutOnlyAuthEntryLocation,
  readAuthContinuation,
} from "../composables/auth/authEntryNavigation";
import { useAuthStore } from "../stores/auth";

type ResetPasswordViewState = "form" | "success" | "expired" | "invalid";
type ResetPasswordResponse = {
  message: string;
};

const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const password = ref("");
const confirmPassword = ref("");
const errorMessage = ref<string | null>(null);
const successMessage = ref<string | null>(null);
const isSubmitting = ref(false);
const state = ref<ResetPasswordViewState>("form");
const continuation = computed(() => readAuthContinuation(route.query, window.history.state));
const forgotPasswordLocation = computed(() =>
  buildAuthContinuationLocation({ name: "forgot-password" }, continuation.value),
);

const token = computed(() => {
  const rawToken = route.query.token;
  return typeof rawToken === "string" && rawToken.trim().length > 0 ? rawToken.trim() : null;
});

function syncViewStateFromToken(currentToken: string | null): void {
  password.value = "";
  confirmPassword.value = "";
  errorMessage.value = null;
  successMessage.value = null;
  isSubmitting.value = false;
  state.value = currentToken ? "form" : "invalid";
}

watch(token, (currentToken) => {
  syncViewStateFromToken(currentToken);
}, { immediate: true });

function resolveValidationMessage(error: ApiError): string {
  return error.message === "Validation error"
    ? "Kontrollera att lösenordet uppfyller kraven och försök igen."
    : error.message;
}

async function submit(): Promise<void> {
  if (isSubmitting.value || state.value !== "form" || !token.value) {
    return;
  }

  errorMessage.value = null;

  if (password.value.length < 8) {
    errorMessage.value = "Lösenordet måste vara minst 8 tecken.";
    return;
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = "Lösenorden matchar inte.";
    return;
  }

  isSubmitting.value = true;

  try {
    const response = await apiPost<ResetPasswordResponse>("/api/v1/auth/reset-password", {
      token: token.value,
      new_password: password.value,
    });
    auth.clear();
    successMessage.value = response.message;
    state.value = "success";
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.code === "INVALID_PASSWORD_RESET_TOKEN") {
        state.value = "invalid";
      } else if (error.code === "PASSWORD_RESET_TOKEN_EXPIRED") {
        state.value = "expired";
      } else if (error.code === "VALIDATION_ERROR") {
        errorMessage.value = resolveValidationMessage(error);
      } else {
        errorMessage.value = error.message;
      }
    } else {
      errorMessage.value =
        error instanceof Error ? error.message : "Det gick inte att återställa lösenordet.";
    }
  } finally {
    isSubmitting.value = false;
  }
}

async function goToAuthEntry(): Promise<void> {
  await router.push(buildSignedOutOnlyAuthEntryLocation(continuation.value));
}
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center px-4">
    <div class="w-full max-w-md">
      <div
        v-if="state === 'form'"
        class="bg-white border border-navy shadow-brutal p-8 space-y-6"
      >
        <header class="space-y-2 text-center">
          <h1 class="font-sans text-xl font-semibold text-navy">
            Återställ lösenord
          </h1>
          <p class="text-sm text-navy/70 leading-relaxed">
            Ange ett nytt lösenord för ditt konto. Länken fungerar bara en gång.
          </p>
        </header>

        <SystemMessage
          v-model="errorMessage"
          variant="error"
        />

        <form
          class="space-y-4"
          @submit.prevent="submit"
        >
          <div class="space-y-2">
            <label
              for="reset-password-new"
              class="text-sm font-semibold text-navy"
            >Nytt lösenord</label>
            <input
              id="reset-password-new"
              v-model="password"
              type="password"
              required
              autocomplete="new-password"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
              :disabled="isSubmitting"
            >
            <p class="text-xs text-navy/60">Minst 8 tecken.</p>
          </div>

          <div class="space-y-2">
            <label
              for="reset-password-confirm"
              class="text-sm font-semibold text-navy"
            >Bekräfta nytt lösenord</label>
            <input
              id="reset-password-confirm"
              v-model="confirmPassword"
              type="password"
              required
              autocomplete="new-password"
              class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
              :disabled="isSubmitting"
            >
          </div>

          <button
            type="submit"
            class="btn-cta w-full"
            :disabled="isSubmitting"
          >
            {{ isSubmitting ? "Återställer lösenord…" : "Återställ lösenord" }}
          </button>
        </form>
      </div>

      <div
        v-else-if="state === 'success'"
        class="bg-white border border-navy shadow-brutal p-12 text-center"
      >
        <div class="flex justify-center mb-6 text-success">
          <IconCheck :size="48" />
        </div>
        <h1 class="font-sans text-xl font-semibold text-navy mb-4">
          Lösenordet är uppdaterat
        </h1>
        <p class="text-navy leading-relaxed">
          {{ successMessage }}
        </p>
        <button
          type="button"
          class="inline-block mt-6 text-navy underline hover:text-burgundy"
          @click="void goToAuthEntry()"
        >
          Gå till inloggning
        </button>
      </div>

      <div
        v-else-if="state === 'expired'"
        class="bg-white border border-navy shadow-brutal p-12 text-center"
      >
        <div class="flex justify-center mb-6 text-warning">
          <IconWarning :size="48" />
        </div>
        <h1 class="font-sans text-xl font-semibold text-navy mb-4">
          Återställningslänken har gått ut
        </h1>
        <p class="text-navy/70 leading-relaxed mb-6">
          Begär en ny återställningslänk för att fortsätta.
        </p>
        <RouterLink
          :to="forgotPasswordLocation"
          class="text-navy underline hover:text-burgundy"
        >
          Begär ny länk
        </RouterLink>
      </div>

      <div
        v-else
        class="bg-white border border-navy shadow-brutal p-12 text-center"
      >
        <div class="flex justify-center mb-6 text-burgundy">
          <IconX :size="48" />
        </div>
        <h1 class="font-sans text-xl font-semibold text-navy mb-4">
          Ogiltig återställningslänk
        </h1>
        <p class="text-navy/70 leading-relaxed mb-6">
          Länken kan redan ha använts eller vara felaktig.
        </p>
        <RouterLink
          :to="forgotPasswordLocation"
          class="text-navy underline hover:text-burgundy"
        >
          Begär en ny länk
        </RouterLink>
      </div>
    </div>
  </div>
</template>
