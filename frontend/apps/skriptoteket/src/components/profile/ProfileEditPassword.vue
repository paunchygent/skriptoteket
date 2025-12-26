<script setup lang="ts">
import { ref } from "vue";

import { isApiError } from "../../api/client";
import { useProfile } from "../../composables/useProfile";
import { useToast } from "../../composables/useToast";
import SystemMessage from "../ui/SystemMessage.vue";

const emit = defineEmits<{
  cancel: [];
  saved: [];
}>();

const { changePassword } = useProfile();
const toast = useToast();

const currentPassword = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const error = ref<string | null>(null);
const isSaving = ref(false);

function clearForm(): void {
  currentPassword.value = "";
  newPassword.value = "";
  confirmPassword.value = "";
}

async function handleSubmit(): Promise<void> {
  if (isSaving.value) return;

  error.value = null;

  if (!currentPassword.value) {
    error.value = "Ange ditt nuvarande lösenord.";
    return;
  }
  if (newPassword.value.length < 8) {
    error.value = "Lösenordet måste vara minst 8 tecken.";
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = "Lösenorden matchar inte.";
    return;
  }

  isSaving.value = true;

  try {
    await changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
    });
    clearForm();
    toast.success("Lösenordet uppdaterades.");
    emit("saved");
  } catch (err: unknown) {
    if (isApiError(err)) {
      error.value = err.message;
    } else if (err instanceof Error) {
      error.value = err.message;
    } else {
      error.value = "Kunde inte uppdatera lösenordet.";
    }
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm">
    <div class="border-b border-navy px-4 py-3">
      <h2 class="text-sm font-semibold text-navy">Ändra lösenord</h2>
      <p class="text-xs text-navy/70">Ange ditt nuvarande lösenord och välj ett nytt</p>
    </div>

    <div class="p-4">
      <SystemMessage
        v-model="error"
        variant="error"
        class="mb-4"
      />

      <form
        class="space-y-4"
        @submit.prevent="handleSubmit"
      >
        <div class="space-y-1">
          <label
            for="edit-current-password"
            class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
          >Nuvarande lösenord</label>
          <input
            id="edit-current-password"
            v-model="currentPassword"
            type="password"
            autocomplete="current-password"
            class="w-full border border-navy bg-white px-3 py-2 text-navy shadow-brutal-sm"
            :disabled="isSaving"
          >
        </div>

        <div class="space-y-1">
          <label
            for="edit-new-password"
            class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
          >Nytt lösenord</label>
          <input
            id="edit-new-password"
            v-model="newPassword"
            type="password"
            autocomplete="new-password"
            class="w-full border border-navy bg-white px-3 py-2 text-navy shadow-brutal-sm"
            :disabled="isSaving"
          >
          <p class="text-xs text-navy/70">Minst 8 tecken.</p>
        </div>

        <div class="space-y-1">
          <label
            for="edit-confirm-password"
            class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
          >Bekräfta nytt lösenord</label>
          <input
            id="edit-confirm-password"
            v-model="confirmPassword"
            type="password"
            autocomplete="new-password"
            class="w-full border border-navy bg-white px-3 py-2 text-navy shadow-brutal-sm"
            :disabled="isSaving"
          >
        </div>

        <div class="flex gap-2 pt-2">
          <button
            type="submit"
            class="btn-primary"
            :disabled="isSaving"
          >
            {{ isSaving ? "Sparar..." : "Uppdatera lösenord" }}
          </button>
          <button
            type="button"
            class="btn-ghost"
            :disabled="isSaving"
            @click="emit('cancel')"
          >
            Avbryt
          </button>
        </div>
      </form>
    </div>
  </section>
</template>
