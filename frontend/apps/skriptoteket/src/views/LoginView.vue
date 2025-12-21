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
  <div>
    <h2>Login</h2>

    <form
      style="display: grid; gap: 12px; max-width: 420px"
      @submit.prevent="onSubmit"
    >
      <label style="display: grid; gap: 6px">
        <span>Email</span>
        <input
          v-model="email"
          type="email"
          autocomplete="username"
          required
          :disabled="isSubmitting"
        >
      </label>

      <label style="display: grid; gap: 6px">
        <span>Password</span>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          :disabled="isSubmitting"
        >
      </label>

      <button
        type="submit"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? "Logging in…" : "Log in" }}
      </button>

      <p
        v-if="submitError"
        style="margin: 0; color: #b00020"
      >
        {{ submitError }}
      </p>
    </form>
  </div>
</template>
