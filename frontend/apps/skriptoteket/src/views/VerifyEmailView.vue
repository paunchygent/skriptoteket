<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { apiPost, isApiError } from "../api/client";
import { IconCheck, IconWarning, IconX } from "../components/icons";

type VerifyState = "loading" | "success" | "expired" | "invalid";

const route = useRoute();
const router = useRouter();

const state = ref<VerifyState>("loading");
const expiredEmail = ref<string | null>(null);
const isResending = ref(false);
const resendSuccess = ref(false);
const countdown = ref(5);

let redirectTimer: ReturnType<typeof setTimeout> | null = null;
let countdownInterval: ReturnType<typeof setInterval> | null = null;

const token = computed(() => {
  const t = route.query.token;
  return typeof t === "string" ? t : null;
});

async function verifyToken(): Promise<void> {
  if (!token.value) {
    state.value = "invalid";
    return;
  }

  try {
    await apiPost<{ message: string }>("/api/v1/auth/verify-email", {
      token: token.value,
    });
    state.value = "success";
    startRedirectCountdown();
  } catch (err: unknown) {
    if (isApiError(err)) {
      if (err.code === "VERIFICATION_TOKEN_EXPIRED") {
        state.value = "expired";
        const details = err.details as { email?: string } | null;
        expiredEmail.value = details?.email ?? null;
      } else {
        state.value = "invalid";
      }
    } else {
      state.value = "invalid";
    }
  }
}

function startRedirectCountdown(): void {
  countdown.value = 5;
  countdownInterval = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0 && countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
  }, 1000);

  redirectTimer = setTimeout(() => {
    router.push("/");
  }, 5000);
}

function cancelRedirect(): void {
  if (redirectTimer) {
    clearTimeout(redirectTimer);
    redirectTimer = null;
  }
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
}

async function resendVerification(): Promise<void> {
  if (!expiredEmail.value || isResending.value) return;

  isResending.value = true;
  try {
    await apiPost<{ message: string }>("/api/v1/auth/resend-verification", {
      email: expiredEmail.value,
    });
    resendSuccess.value = true;
  } catch {
    // Silent fail - backend always returns success for security
  } finally {
    isResending.value = false;
  }
}

onMounted(() => {
  verifyToken();
});

onUnmounted(() => {
  cancelRedirect();
});
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center px-4">
    <div class="w-full max-w-md">
      <!-- LOADING STATE -->
      <div
        v-if="state === 'loading'"
        class="bg-white border border-navy shadow-brutal p-12 text-center"
      >
        <div class="flex justify-center mb-6">
          <span
            class="inline-block w-12 h-12 border-4 border-navy/20 border-t-navy rounded-full animate-spin"
          />
        </div>
        <p class="text-navy text-lg">Verifierar din e-postadress...</p>
      </div>

      <!-- SUCCESS STATE -->
      <div
        v-else-if="state === 'success'"
        class="bg-white border border-navy shadow-brutal p-12 text-center"
      >
        <div class="flex justify-center mb-6 text-success">
          <IconCheck :size="48" />
        </div>
        <h1 class="font-sans text-xl font-semibold text-navy mb-4">
          Ditt konto är verifierat.
        </h1>
        <p class="text-navy leading-relaxed">
          Välkommen att
          <RouterLink
            to="/"
            class="text-navy underline hover:text-burgundy"
            @click="cancelRedirect"
          >
            logga in
          </RouterLink>.
        </p>
        <p class="text-sm text-navy/60 mt-6">
          Omdirigeras om {{ countdown }} sekund{{ countdown !== 1 ? "er" : "" }}...
        </p>
      </div>

      <!-- EXPIRED STATE -->
      <div
        v-else-if="state === 'expired'"
        class="bg-white border border-navy shadow-brutal p-12 text-center"
      >
        <div class="flex justify-center mb-6 text-warning">
          <IconWarning :size="48" />
        </div>
        <h1 class="font-sans text-xl font-semibold text-navy mb-4">
          Verifieringslänken har gått ut
        </h1>
        <p class="text-navy/70 leading-relaxed mb-6">
          Länken är giltig i 24 timmar.
        </p>

        <div v-if="resendSuccess">
          <p class="text-success text-sm">
            Ett nytt verifieringsmail har skickats.
          </p>
        </div>
        <div v-else-if="expiredEmail">
          <button
            type="button"
            class="btn-cta"
            :disabled="isResending"
            @click="resendVerification"
          >
            {{ isResending ? "Skickar..." : "SKICKA NY LÄNK" }}
          </button>
        </div>
        <div v-else>
          <p class="text-navy/70 text-sm">
            Kontakta support om du behöver hjälp.
          </p>
        </div>
      </div>

      <!-- INVALID STATE -->
      <div
        v-else
        class="bg-white border border-navy shadow-brutal p-12 text-center"
      >
        <div class="flex justify-center mb-6 text-burgundy">
          <IconX :size="48" />
        </div>
        <h1 class="font-sans text-xl font-semibold text-navy mb-4">
          Ogiltig verifieringslänk
        </h1>
        <p class="text-navy/70 leading-relaxed mb-6">
          Länken kan redan ha använts eller vara felaktig.
        </p>
        <RouterLink
          to="/"
          class="text-navy underline hover:text-burgundy text-sm"
        >
          Ta mig tillbaka till startsidan
        </RouterLink>
      </div>
    </div>
  </div>
</template>
