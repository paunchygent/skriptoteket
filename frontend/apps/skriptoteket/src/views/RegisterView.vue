<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

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

onMounted(async () => {
  await auth.bootstrap();
  if (auth.isAuthenticated) {
    await router.replace("/");
  }
});

async function submit(): Promise<void> {
  if (isSubmitting.value) return;

  errorMessage.value = null;

  if (!firstName.value.trim() || !lastName.value.trim()) {
    errorMessage.value = "Förnamn och efternamn måste anges.";
    return;
  }

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
    await auth.register({
      email: email.value,
      password: password.value,
      firstName: firstName.value,
      lastName: lastName.value,
    });
    await router.push("/");
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
      <p class="page-description">Registrera dig för att få tillgång till verktygen i Skriptoteket.</p>
    </header>

    <div
      v-if="errorMessage"
      class="p-3 border border-burgundy bg-white shadow-brutal-sm text-burgundy text-sm"
    >
      {{ errorMessage }}
    </div>

    <form
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
          class="w-full border border-navy bg-white px-3 py-2 shadow-brutal-sm text-navy"
          :disabled="isSubmitting"
        >
      </div>

      <div class="space-y-2">
        <label
          for="register-password"
          class="text-sm font-semibold text-navy"
        >Lösenord</label>
        <input
          id="register-password"
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
          for="register-confirm"
          class="text-sm font-semibold text-navy"
        >Bekräfta lösenord</label>
        <input
          id="register-confirm"
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
        {{ isSubmitting ? "Skapar konto…" : "Skapa konto" }}
      </button>
    </form>
  </div>
</template>
