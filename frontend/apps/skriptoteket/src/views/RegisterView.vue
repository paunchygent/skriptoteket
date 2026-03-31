<script setup lang="ts">
/**
 * Public registration view.
 *
 * This route owns the early-release account-creation form and the follow-up
 * verify-email confirmation state used by the public auth flow.
 */

import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import AuthPasswordField from "../components/auth/AuthPasswordField.vue";
import { IconCheck } from "../components/icons";
import { useRegistrationValidation } from "../composables/auth/useRegistrationValidation";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();

const firstName = ref("");
const lastName = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");

const isSubmitting = ref(false);
const errorMessage = ref<string | null>(null);
const registrationMessage = ref<string | null>(null);
const {
  canSubmit,
  confirmPasswordError,
  emailError,
  isChecking,
  passwordError,
  validationIssue,
} = useRegistrationValidation({
  email,
  password,
  confirmPassword,
});

const submitDisabled = computed(() => {
  if (isSubmitting.value) {
    return true;
  }
  if (!firstName.value.trim() || !lastName.value.trim()) {
    return true;
  }
  return !canSubmit.value;
});

onMounted(async () => {
  await auth.bootstrap();
  if (auth.isAuthenticated) {
    await router.replace("/");
  }
});

async function submit(): Promise<void> {
  if (isSubmitting.value) return;

  errorMessage.value = null;
  registrationMessage.value = null;

  if (!firstName.value.trim() || !lastName.value.trim()) {
    errorMessage.value = "Förnamn och efternamn måste anges.";
    return;
  }

  if (emailError.value) {
    errorMessage.value = emailError.value;
    return;
  }

  if (!validationIssue.value && email.value.trim() === "") {
    errorMessage.value = "Ange en giltig tjänsteadress.";
    return;
  }

  if (passwordError.value) {
    errorMessage.value = passwordError.value;
    return;
  }

  if (validationIssue.value && password.value.length < 8) {
    errorMessage.value = "Lösenordet måste vara minst 8 tecken.";
    return;
  }

  if (confirmPasswordError.value) {
    errorMessage.value = confirmPasswordError.value;
    return;
  }

  if (!canSubmit.value) {
    errorMessage.value = "Kontrollera uppgifterna innan du skapar konto.";
    return;
  }

  isSubmitting.value = true;

  try {
    const result = await auth.register({
      email: email.value,
      password: password.value,
      firstName: firstName.value,
      lastName: lastName.value,
    });
    registrationMessage.value = result.message;
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof Error ? error.message : "Kunde inte skapa konto.";
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <div class="max-w-xl mx-auto space-y-6">
    <header class="space-y-2">
      <h1 class="page-title">Skapa konto</h1>
      <p class="page-description">
        Just nu är registrering endast öppen för anställda hos kommuner och enskilda
        skolhuvudmän.
      </p>
    </header>

    <div
      v-if="registrationMessage"
      class="space-y-4 border border-navy bg-white p-6 shadow-brutal"
    >
      <div class="flex items-center gap-3 text-navy">
        <IconCheck :size="24" />
        <h2 class="text-lg font-semibold">
          Kontrollera din e-post
        </h2>
      </div>
      <p class="text-sm leading-relaxed text-navy/80">
        {{ registrationMessage }}
      </p>
      <p class="text-sm leading-relaxed text-navy/80">
        Om du inte ser något mejl från <strong>noreply@hule.education</strong> i din inkorg,
        kontrollera din skräppost.
      </p>
      <RouterLink
        to="/"
        class="inline-flex text-sm font-semibold text-navy underline hover:text-burgundy"
      >
        Till startsidan
      </RouterLink>
    </div>

    <div
      v-else-if="errorMessage"
      class="p-3 border border-burgundy bg-white shadow-brutal-sm text-burgundy text-sm"
    >
      {{ errorMessage }}
    </div>

    <form
      v-if="!registrationMessage"
      class="space-y-4"
      @submit.prevent="submit"
    >
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <label
            for="first-name"
            class="text-sm font-semibold text-navy"
          >Förnamn</label>
          <input
            id="first-name"
            v-model="firstName"
            type="text"
            required
            autocomplete="given-name"
            class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
            :disabled="isSubmitting"
          >
        </div>

        <div class="space-y-2">
          <label
            for="last-name"
            class="text-sm font-semibold text-navy"
          >Efternamn</label>
          <input
            id="last-name"
            v-model="lastName"
            type="text"
            required
            autocomplete="family-name"
            class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
            :disabled="isSubmitting"
          >
        </div>
      </div>

      <div class="space-y-2">
        <label
          for="register-email"
          class="text-sm font-semibold text-navy"
        >E-post</label>
        <input
          id="register-email"
          v-model="email"
          type="email"
          required
          autocomplete="username"
          class="w-full border bg-white px-3 py-2 shadow-brutal-sm text-navy"
          :class="emailError ? 'border-burgundy' : 'border-navy'"
          :disabled="isSubmitting"
          :aria-invalid="emailError ? 'true' : 'false'"
          aria-describedby="register-email-help"
        >
        <p
          id="register-email-help"
          class="text-xs"
          :class="emailError ? 'text-burgundy' : 'text-navy/60'"
        >
          {{
            emailError ??
              "Endast anställda hos kommuner och enskilda huvudmän kan registrera sig just nu. Använd din e-postadress från kommun eller enskild huvudman."
          }}
        </p>
      </div>

      <div
        v-if="validationIssue"
        class="p-3 border border-navy/20 bg-white shadow-brutal-sm text-sm text-navy/80"
      >
        {{ validationIssue }}
      </div>

      <AuthPasswordField
        id="register-password"
        v-model="password"
        label="Lösenord"
        autocomplete="new-password"
        :required="true"
        :disabled="isSubmitting"
        :error="passwordError"
        hint="Minst 8 tecken."
      />

      <AuthPasswordField
        id="register-confirm"
        v-model="confirmPassword"
        label="Bekräfta lösenord"
        autocomplete="new-password"
        :required="true"
        :disabled="isSubmitting"
        :error="confirmPasswordError"
        hint="Skriv samma lösenord en gång till."
      />

      <p
        v-if="isChecking"
        class="text-xs text-navy/60"
      >
        Kontrollerar e-postadress och lösenord…
      </p>

      <button
        type="submit"
        class="btn-cta w-full"
        :disabled="submitDisabled"
      >
        {{ isSubmitting ? "Skapar konto…" : "Skapa konto" }}
      </button>
    </form>
  </div>
</template>
