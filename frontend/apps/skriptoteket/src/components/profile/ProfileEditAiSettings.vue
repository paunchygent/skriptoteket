<script setup lang="ts">
import { onMounted, ref } from "vue";
import { storeToRefs } from "pinia";

import { useToast } from "../../composables/useToast";
import { useAiStore, type RemoteFallbackPreference } from "../../stores/ai";

const emit = defineEmits<{
  cancel: [];
  saved: [];
}>();

const ai = useAiStore();
const { remoteFallbackPreference } = storeToRefs(ai);
const toast = useToast();

type RemoteFallbackSelection = Extract<RemoteFallbackPreference, "allow" | "deny"> | null;

const selection = ref<RemoteFallbackSelection>(null);
const isSaving = ref(false);

onMounted(() => {
  selection.value = remoteFallbackPreference.value === "unset" ? null : remoteFallbackPreference.value;
});

async function handleSubmit(): Promise<void> {
  if (isSaving.value) return;
  if (!selection.value) {
    toast.warning("Välj om du vill aktivera eller stänga av externa AI-API:er.");
    return;
  }
  isSaving.value = true;

  try {
    await ai.persistRemoteFallbackPreference(selection.value);
    ai.setRemoteFallbackPreference(selection.value);
    toast.success("AI-inställningarna uppdaterades.");
    emit("saved");
  } catch (error: unknown) {
    toast.failure(error instanceof Error ? error.message : "Kunde inte spara AI-inställningarna.");
  } finally {
    isSaving.value = false;
  }
}
</script>

<template>
  <section class="border border-navy bg-white shadow-brutal-sm">
    <div class="border-b border-navy px-4 py-3">
      <h2 class="text-sm font-semibold text-navy">AI-inställningar</h2>
      <p class="text-xs text-navy/70">Styr om kodassistenten får använda externa AI-API:er.</p>
    </div>

    <div class="p-4 space-y-4">
      <div class="panel-inset-canvas p-3 text-xs text-navy/70">
        Externa AI-API:er kan skicka innehåll utanför servern. Aktivera eller stäng av externa AI-API:er.
      </div>

      <form
        class="space-y-4"
        @submit.prevent="handleSubmit"
      >
        <fieldset class="space-y-2">
          <legend class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Externa AI-API:er
          </legend>

          <label class="flex items-start gap-3 border border-navy/20 bg-canvas px-3 py-2">
            <input
              v-model="selection"
              type="radio"
              name="remote-fallback"
              value="allow"
              class="mt-0.5"
              :disabled="isSaving"
            >
            <span class="text-sm text-navy">
              <span class="font-semibold">Aktivera</span>
              <span class="block text-xs text-navy/70">
                Kodassistenten kan använda externa AI-API:er om lokala modeller är nere/överbelastade.
              </span>
            </span>
          </label>

          <label class="flex items-start gap-3 border border-navy/20 bg-canvas px-3 py-2">
            <input
              v-model="selection"
              type="radio"
              name="remote-fallback"
              value="deny"
              class="mt-0.5"
              :disabled="isSaving"
            >
            <span class="text-sm text-navy">
              <span class="font-semibold">Stäng av</span>
              <span class="block text-xs text-navy/70">Kodassistenten använder endast lokala modeller.</span>
            </span>
          </label>
        </fieldset>

        <div class="flex gap-2 pt-2">
          <button
            type="submit"
            class="btn-primary"
            :disabled="isSaving || !selection"
          >
            Spara
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
