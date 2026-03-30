<script setup lang="ts">
/**
 * Unauthenticated password-reset request screen.
 *
 * This view exposes the public forgot-password flow while keeping the backend
 * authoritative for eligibility, throttling, and generic success semantics.
 */

import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiPost } from "../api/client";
import SystemMessage from "../components/ui/SystemMessage.vue";
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
  isSubmitting.value = true;

  try {
    const response = await apiPost<ForgotPasswordResponse>("/api/v1/auth/forgot-password", {
      email: normalizedEmail,
    });
    successMessage.value = response.message;
  } catch (error: unknown) {
    errorMessage.value =
      error instanceof Error ? error.message : "Det gick inte att begära en återställningslänk.";
  } finally {
    isSubmitting.value = false;
  }
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
  </div>
</template>
