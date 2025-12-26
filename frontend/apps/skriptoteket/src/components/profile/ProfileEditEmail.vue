<script setup lang="ts">
import { ref } from "vue";

import { isApiError } from "../../api/client";
import { useProfile } from "../../composables/useProfile";
import { useToast } from "../../composables/useToast";
import SystemMessage from "../ui/SystemMessage.vue";

const props = defineProps<{
  currentEmail: string;
}>();

const emit = defineEmits<{
  cancel: [];
  saved: [];
}>();

const { changeEmail } = useProfile();
const toast = useToast();

const newEmail = ref("");
const error = ref<string | null>(null);
const isSaving = ref(false);

async function handleSubmit(): Promise<void> {
  if (isSaving.value) return;

  error.value = null;

  const trimmed = newEmail.value.trim().toLowerCase();
  if (!trimmed) {
    error.value = "Ange en ny e-postadress.";
    return;
  }
  if (trimmed === props.currentEmail.toLowerCase()) {
    error.value = "E-postadressen är redan registrerad.";
    return;
  }

  isSaving.value = true;

  try {
    await changeEmail({ email: trimmed });
    toast.success("E-postadressen uppdaterades.");
    emit("saved");
  } catch (err: unknown) {
    if (isApiError(err)) {
      error.value = err.message;
    } else if (err instanceof Error) {
      error.value = err.message;
    } else {
      error.value = "Kunde inte uppdatera e-postadressen.";
    }
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm">
    <div class="border-b border-navy px-4 py-3">
      <h2 class="text-sm font-semibold text-navy">Ändra e-postadress</h2>
      <p class="text-xs text-navy/70">Nuvarande: {{ currentEmail }}</p>
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
            for="edit-email"
            class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
          >Ny e-postadress</label>
          <input
            id="edit-email"
            v-model="newEmail"
            type="email"
            autocomplete="email"
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
            {{ isSaving ? "Sparar..." : "Uppdatera e-post" }}
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
