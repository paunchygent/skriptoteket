<script setup lang="ts">
import { onMounted, ref } from "vue";

import { isApiError } from "../../api/client";
import type { components } from "../../api/openapi";
import { useProfile } from "../../composables/useProfile";
import { useToast } from "../../composables/useToast";
import SystemMessage from "../ui/SystemMessage.vue";

type UserProfile = components["schemas"]["UserProfile"];

const props = defineProps<{
  profile: UserProfile;
}>();

const emit = defineEmits<{
  cancel: [];
  saved: [];
}>();

const { updateProfile } = useProfile();
const toast = useToast();

const firstName = ref("");
const lastName = ref("");
const displayName = ref("");
const locale = ref("sv-SE");

const error = ref<string | null>(null);
const isSaving = ref(false);

function syncFromProps(): void {
  firstName.value = props.profile.first_name ?? "";
  lastName.value = props.profile.last_name ?? "";
  displayName.value = props.profile.display_name ?? "";
  locale.value = props.profile.locale ?? "sv-SE";
}

async function handleSubmit(): Promise<void> {
  if (isSaving.value) return;

  error.value = null;

  if (!firstName.value.trim() || !lastName.value.trim()) {
    error.value = "Förnamn och efternamn krävs.";
    return;
  }

  isSaving.value = true;

  try {
    await updateProfile({
      first_name: firstName.value.trim(),
      last_name: lastName.value.trim(),
      display_name: displayName.value.trim() || null,
      locale: locale.value,
    });
    toast.success("Profilen uppdaterades.");
    emit("saved");
  } catch (err: unknown) {
    if (isApiError(err)) {
      error.value = err.message;
    } else if (err instanceof Error) {
      error.value = err.message;
    } else {
      error.value = "Kunde inte uppdatera profilen.";
    }
  } finally {
    isSaving.value = false;
  }
}

onMounted(() => {
  syncFromProps();
});
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm">
    <div class="border-b border-navy px-4 py-3">
      <h2 class="text-sm font-semibold text-navy">Redigera personlig information</h2>
      <p class="text-xs text-navy/70">Uppdatera namn och visningsnamn</p>
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
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-1">
            <label
              for="edit-first-name"
              class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
            >Förnamn</label>
            <input
              id="edit-first-name"
              v-model="firstName"
              type="text"
              required
              class="w-full border border-navy bg-white px-3 py-2 text-navy shadow-brutal-sm"
              :disabled="isSaving"
            >
          </div>
          <div class="space-y-1">
            <label
              for="edit-last-name"
              class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
            >Efternamn</label>
            <input
              id="edit-last-name"
              v-model="lastName"
              type="text"
              required
              class="w-full border border-navy bg-white px-3 py-2 text-navy shadow-brutal-sm"
              :disabled="isSaving"
            >
          </div>
        </div>

        <div class="space-y-1">
          <label
            for="edit-display-name"
            class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
          >Visningsnamn</label>
          <input
            id="edit-display-name"
            v-model="displayName"
            type="text"
            placeholder="Valfritt"
            class="w-full border border-navy bg-white px-3 py-2 text-navy shadow-brutal-sm"
            :disabled="isSaving"
          >
        </div>

        <div class="space-y-1">
          <label
            for="edit-locale"
            class="block text-xs font-semibold uppercase tracking-wide text-navy/70"
          >Språk</label>
          <select
            id="edit-locale"
            v-model="locale"
            class="w-full border border-navy bg-white px-3 py-2 text-navy shadow-brutal-sm"
            :disabled="isSaving"
          >
            <option value="sv-SE">Svenska (sv-SE)</option>
            <option value="en-US">English (en-US)</option>
          </select>
        </div>

        <div class="flex gap-2 pt-2">
          <button
            type="submit"
            class="btn-primary"
            :disabled="isSaving"
          >
            {{ isSaving ? "Sparar..." : "Spara" }}
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
