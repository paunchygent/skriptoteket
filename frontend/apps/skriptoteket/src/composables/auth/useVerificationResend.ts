/**
 * Shared resend-verification state for anonymous and login-recovery surfaces.
 *
 * This composable keeps the frontend affordance aligned with the backend's
 * generic-success contract while offering a lightweight client-side cooldown.
 */

import { computed, onUnmounted, ref } from "vue";

import { apiPost } from "../../api/client";

type ResendVerificationResponse = {
  message: string;
};

const DEFAULT_COOLDOWN_SECONDS = 60;

export function useVerificationResend() {
  const isSubmitting = ref(false);
  const successMessage = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);
  const cooldownRemainingSeconds = ref(0);

  let cooldownInterval: ReturnType<typeof setInterval> | null = null;

  const canResend = computed(() => !isSubmitting.value && cooldownRemainingSeconds.value === 0);

  function clearMessages(): void {
    successMessage.value = null;
    errorMessage.value = null;
  }

  function stopCooldown(): void {
    if (cooldownInterval) {
      clearInterval(cooldownInterval);
      cooldownInterval = null;
    }
  }

  function startCooldown(seconds = DEFAULT_COOLDOWN_SECONDS): void {
    stopCooldown();
    cooldownRemainingSeconds.value = seconds;
    cooldownInterval = setInterval(() => {
      if (cooldownRemainingSeconds.value <= 1) {
        cooldownRemainingSeconds.value = 0;
        stopCooldown();
        return;
      }
      cooldownRemainingSeconds.value -= 1;
    }, 1000);
  }

  async function resend(email: string): Promise<void> {
    const normalizedEmail = email.trim();
    if (!normalizedEmail || !canResend.value) {
      return;
    }

    clearMessages();
    isSubmitting.value = true;

    try {
      const response = await apiPost<ResendVerificationResponse>("/api/v1/auth/resend-verification", {
        email: normalizedEmail,
      });
      successMessage.value = response.message;
      startCooldown();
    } catch (error: unknown) {
      errorMessage.value =
        error instanceof Error
          ? error.message
          : "Det gick inte att begära ett nytt verifieringsmejl.";
    } finally {
      isSubmitting.value = false;
    }
  }

  onUnmounted(() => {
    stopCooldown();
  });

  return {
    canResend,
    clearMessages,
    cooldownRemainingSeconds,
    errorMessage,
    isSubmitting,
    resend,
    successMessage,
  };
}
