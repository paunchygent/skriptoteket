/**
 * Registration preflight validation for the public signup form.
 *
 * This composable debounces backend-backed email/password validation so the
 * register view can show authoritative feedback before submit while still
 * falling back to local checks if the preflight endpoint is temporarily
 * unavailable.
 */

import { computed, ref, watch, type Ref } from "vue";

import { apiPost, isApiError } from "../../api/client";

type ValidationStatus = "valid" | "invalid" | "incomplete";

type ValidationField = {
  status: ValidationStatus;
  message: string | null;
};

type ValidationResponse = {
  email: ValidationField;
  password: ValidationField;
};

const DEBOUNCE_MS = 300;

const INCOMPLETE_FIELD: ValidationField = {
  status: "incomplete",
  message: null,
};

export function useRegistrationValidation(params: {
  email: Ref<string>;
  password: Ref<string>;
  confirmPassword: Ref<string>;
}) {
  const emailState = ref<ValidationField>({ ...INCOMPLETE_FIELD });
  const passwordState = ref<ValidationField>({ ...INCOMPLETE_FIELD });
  const isChecking = ref(false);
  const validationIssue = ref<string | null>(null);

  const confirmPasswordError = computed(() => {
    if (params.confirmPassword.value === "") {
      return null;
    }
    if (params.confirmPassword.value !== params.password.value) {
      return "Lösenorden matchar inte.";
    }
    return null;
  });

  const emailError = computed(() =>
    emailState.value.status === "invalid" ? emailState.value.message : null,
  );
  const passwordError = computed(() =>
    passwordState.value.status === "invalid" ? passwordState.value.message : null,
  );

  const canSubmit = computed(() => {
    if (params.confirmPassword.value === "" || confirmPasswordError.value) {
      return false;
    }

    if (validationIssue.value) {
      return params.email.value.trim() !== "" && params.password.value.length >= 8;
    }

    return emailState.value.status === "valid" && passwordState.value.status === "valid";
  });

  watch(
    [params.email, params.password],
    ([nextEmail, nextPassword], _previous, onCleanup) => {
      const normalizedEmail = nextEmail.trim();
      const normalizedPassword = nextPassword;
      validationIssue.value = null;

      if (normalizedEmail === "" && normalizedPassword === "") {
        emailState.value = { ...INCOMPLETE_FIELD };
        passwordState.value = { ...INCOMPLETE_FIELD };
        isChecking.value = false;
        return;
      }

      let cancelled = false;
      const timerId = window.setTimeout(async () => {
        if (cancelled) {
          return;
        }

        isChecking.value = true;

        try {
          const response = await apiPost<ValidationResponse>("/api/v1/auth/register/validate", {
            email: normalizedEmail || null,
            password: normalizedPassword || null,
          });

          if (cancelled) {
            return;
          }

          emailState.value = response.email;
          passwordState.value = response.password;
        } catch (error: unknown) {
          if (cancelled) {
            return;
          }

          validationIssue.value = isApiError(error)
            ? error.message
            : "Förhandskontrollen kunde inte köras just nu. Du kan fortfarande försöka skapa konto.";
        } finally {
          if (!cancelled) {
            isChecking.value = false;
          }
        }
      }, DEBOUNCE_MS);

      onCleanup(() => {
        cancelled = true;
        window.clearTimeout(timerId);
        isChecking.value = false;
      });
    },
  );

  return {
    canSubmit,
    confirmPasswordError,
    emailError,
    emailState,
    isChecking,
    passwordError,
    passwordState,
    validationIssue,
  };
}
