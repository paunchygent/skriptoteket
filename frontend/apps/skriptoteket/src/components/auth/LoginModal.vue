<script setup lang="ts">
import { computed, ref } from "vue";

import { useAuthStore } from "../../stores/auth";

const props = defineProps<{
  isOpen: boolean;
}>();

const emit = defineEmits<{
  close: [];
  success: [];
}>();

const auth = useAuthStore();

const email = ref("");
const password = ref("");
const submitError = ref<string | null>(null);
const isSubmitting = computed(() => auth.status === "loading");

function closeModal(): void {
  email.value = "";
  password.value = "";
  submitError.value = null;
  emit("close");
}

async function onSubmit(): Promise<void> {
  submitError.value = null;
  try {
    await auth.login({ email: email.value, password: password.value });
    closeModal();
    emit("success");
  } catch (error: unknown) {
    submitError.value =
      error instanceof Error ? error.message : "Inloggningen misslyckades";
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="props.isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy/40"
        role="dialog"
        aria-modal="true"
        aria-labelledby="login-modal-title"
        :aria-describedby="submitError ? 'login-modal-error' : undefined"
        @click.self="closeModal"
      >
        <div
          class="relative w-full max-w-sm mx-4 p-6 bg-canvas border border-navy shadow-brutal"
        >
          <button
            type="button"
            class="absolute top-3 right-3 text-navy/60 hover:text-navy text-xl leading-none"
            @click="closeModal"
          >
            &times;
          </button>

          <h2
            id="login-modal-title"
            class="text-xl font-semibold text-navy"
          >
            Logga in
          </h2>

          <div
            v-if="submitError"
            id="login-modal-error"
            class="mt-4 p-3 border border-error bg-white text-error text-sm"
          >
            {{ submitError }}
          </div>

          <form
            class="mt-5 space-y-4"
            @submit.prevent="onSubmit"
          >
            <div>
              <label
                class="block text-sm font-semibold text-navy mb-1"
                for="modal-email"
              >
                E-post
              </label>
              <input
                id="modal-email"
                v-model="email"
                type="email"
                autocomplete="username"
                required
                class="w-full px-3 py-2 border border-navy bg-white text-navy"
                :disabled="isSubmitting"
              >
            </div>

            <div>
              <label
                class="block text-sm font-semibold text-navy mb-1"
                for="modal-password"
              >
                Lösenord
              </label>
              <input
                id="modal-password"
                v-model="password"
                type="password"
                autocomplete="current-password"
                required
                class="w-full px-3 py-2 border border-navy bg-white text-navy"
                :disabled="isSubmitting"
              >
            </div>

            <button
              type="submit"
              class="w-full px-4 py-2 bg-navy text-canvas border border-navy font-semibold uppercase tracking-wide hover:bg-burgundy transition-colors disabled:opacity-50"
              :disabled="isSubmitting"
            >
              {{ isSubmitting ? "Loggar in…" : "Logga in" }}
            </button>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--huleedu-duration-default) var(--huleedu-ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
