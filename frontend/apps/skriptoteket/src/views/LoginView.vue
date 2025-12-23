<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const email = ref("");
const password = ref("");
const submitError = ref<string | null>(null);

const nextPath = computed(() => {
  const next = route.query.next;
  if (typeof next !== "string") {
    return null;
  }
  if (!next.startsWith("/")) {
    return null;
  }
  if (next.startsWith("/login")) {
    return null;
  }
  return next;
});

const isSubmitting = computed(() => auth.status === "loading");

async function onSubmit(): Promise<void> {
  submitError.value = null;

  try {
    await auth.login({ email: email.value, password: password.value });
    await router.replace(nextPath.value ?? "/");
  } catch (error: unknown) {
    submitError.value = error instanceof Error ? error.message : "Login failed";
  }
}
</script>

<template>
  <div class="max-w-md">
    <h1 class="text-2xl font-semibold text-navy">
      Logga in
    </h1>
    <p class="mt-1 text-sm text-navy/60">
      Logga in för att fortsätta.
    </p>

    <div
      v-if="submitError"
      class="mt-4 p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
    >
      {{ submitError }}
    </div>

    <form
      class="mt-6 p-4 border border-navy bg-white shadow-brutal-sm space-y-4"
      @submit.prevent="onSubmit"
    >
      <div class="space-y-1">
        <label
          class="block text-sm font-semibold text-navy"
          for="email"
        >E-post</label>
        <input
          id="email"
          v-model="email"
          type="email"
          autocomplete="username"
          required
          class="w-full px-3 py-2 border border-navy bg-white shadow-brutal-sm text-navy placeholder:text-navy/40"
          :disabled="isSubmitting"
        >
      </div>

      <div class="space-y-1">
        <label
          class="block text-sm font-semibold text-navy"
          for="password"
        >Lösenord</label>
        <input
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          class="w-full px-3 py-2 border border-navy bg-white shadow-brutal-sm text-navy placeholder:text-navy/40"
          :disabled="isSubmitting"
        >
      </div>

      <button
        type="submit"
        class="w-full px-4 py-2 border border-navy bg-burgundy text-canvas shadow-brutal font-semibold uppercase tracking-wide btn-secondary-hover transition-colors disabled:opacity-50"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? "Loggar in…" : "Logga in" }}
      </button>
    </form>
  </div>
</template>
