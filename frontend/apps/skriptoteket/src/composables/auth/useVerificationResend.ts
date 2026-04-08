/**
 * Shared resend-verification state for anonymous and login-recovery surfaces.
 *
 * This composable keeps the frontend affordance aligned with the backend's
 * generic-success contract while leaving cooldown truth to the backend.
 */

import { ref } from "vue";

import { apiPost } from "../../api/client";

type ResendVerificationResponse = {
  message: string;
};

type ResendVerificationPayload = {
  next?: string;
  classroom_planner_entry_origin?: "dashboard" | "catalog";
};

export function useVerificationResend() {
  const isSubmitting = ref(false);
  const successMessage = ref<string | null>(null);
  const errorMessage = ref<string | null>(null);

  function clearMessages(): void {
    successMessage.value = null;
    errorMessage.value = null;
  }

  async function resend(email: string, continuation: ResendVerificationPayload = {}): Promise<void> {
    const normalizedEmail = email.trim();
    if (!normalizedEmail || isSubmitting.value) {
      return;
    }

    clearMessages();
    isSubmitting.value = true;

    try {
      const response = await apiPost<ResendVerificationResponse>("/api/v1/auth/resend-verification", {
        email: normalizedEmail,
        ...continuation,
      });
      successMessage.value = response.message;
    } catch (error: unknown) {
      errorMessage.value =
        error instanceof Error
          ? error.message
          : "Det gick inte att begära ett nytt verifieringsmejl.";
    } finally {
      isSubmitting.value = false;
    }
  }

  return {
    clearMessages,
    errorMessage,
    isSubmitting,
    resend,
    successMessage,
  };
}
