<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { storeToRefs } from "pinia";

import { useToast } from "../../composables/useToast";
import { useAiStore, type InlineCompletionProviderPreference, type RemoteFallbackPreference } from "../../stores/ai";

const emit = defineEmits<{
  cancel: [];
  saved: [];
}>();

const ai = useAiStore();
const {
  remoteFallbackPreference,
  inlineCompletionProviderPreference,
  remoteProvidersEnabled,
  completionExternalAvailable,
  completionLocalAvailable,
} = storeToRefs(ai);
const toast = useToast();

type RemoteFallbackSelection = Extract<RemoteFallbackPreference, "allow" | "deny"> | null;
type CompletionProviderSelection = Extract<InlineCompletionProviderPreference, "local" | "external">;

const selection = ref<RemoteFallbackSelection>(null);
const completionSelection = ref<CompletionProviderSelection>("local");
const isSaving = ref(false);

watch(
  () =>
    [
      remoteProvidersEnabled.value,
      completionExternalAvailable.value,
      completionLocalAvailable.value,
      selection.value,
    ] as const,
  ([providersEnabled, externalAvailable, localAvailable, remoteFallbackSelection]) => {
    if (!providersEnabled || remoteFallbackSelection !== "allow") {
      if (completionSelection.value === "external") {
        completionSelection.value = "local";
      }
      return;
    }

    if (!localAvailable && externalAvailable) {
      completionSelection.value = "external";
    }
  },
);

onMounted(() => {
  selection.value = remoteFallbackPreference.value === "unset" ? null : remoteFallbackPreference.value;

  if (inlineCompletionProviderPreference.value !== "unset") {
    completionSelection.value = inlineCompletionProviderPreference.value;
    return;
  }

  const canUseExternal =
    remoteProvidersEnabled.value &&
    selection.value === "allow" &&
    completionExternalAvailable.value;
  if (canUseExternal) {
    completionSelection.value = "external";
    return;
  }

  completionSelection.value = "local";
});

async function handleSubmit(): Promise<void> {
  if (isSaving.value) return;
  if (remoteProvidersEnabled.value && !selection.value) {
    toast.warning("Välj om du vill aktivera eller stänga av externa AI-API:er.");
    return;
  }
  isSaving.value = true;

  try {
    await ai.persistAiSettings({
      remote_fallback_preference: remoteProvidersEnabled.value ? selection.value ?? undefined : undefined,
      inline_completion_provider_preference: completionSelection.value,
    });
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
  <section class="expand-left-40 border border-navy bg-white shadow-brutal-sm">
    <div class="border-b border-navy px-4 py-3">
      <h2 class="text-sm font-semibold text-navy">AI-inställningar</h2>
      <p class="text-xs text-navy/70">Styr om kodassistenten får använda externa AI-API:er.</p>
    </div>

    <div class="p-4 space-y-4">
      <div
        v-if="!remoteProvidersEnabled"
        class="panel-inset-canvas p-3 text-xs text-navy/70"
      >
        Systemadministratören tillåter inte externa AI-modeller i den här miljön. Kontakta din administratör om du har
        frågor.
      </div>

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
              :disabled="isSaving || !remoteProvidersEnabled"
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
              :disabled="isSaving || !remoteProvidersEnabled"
            >
            <span class="text-sm text-navy">
              <span class="font-semibold">Stäng av</span>
              <span class="block text-xs text-navy/70">Kodassistenten använder endast lokala modeller.</span>
            </span>
          </label>
        </fieldset>

        <fieldset class="space-y-2">
          <legend class="text-xs font-semibold uppercase tracking-wide text-navy/70">
            Inline completions
          </legend>

          <label class="flex items-start gap-3 border border-navy/20 bg-canvas px-3 py-2">
            <input
              v-model="completionSelection"
              type="radio"
              name="completion-provider"
              value="local"
              class="mt-0.5"
              :disabled="isSaving || !completionLocalAvailable"
            >
            <span class="text-sm text-navy">
              <span class="font-semibold">Lokal (Devstral)</span>
              <span class="block text-xs text-navy/70">
                <template v-if="completionLocalAvailable">Kör completions via lokala modeller.</template>
                <template v-else>Inte tillgänglig i den här miljön.</template>
              </span>
            </span>
          </label>

          <label
            class="flex items-start gap-3 border border-navy/20 bg-canvas px-3 py-2"
          >
            <input
              v-model="completionSelection"
              type="radio"
              name="completion-provider"
              value="external"
              class="mt-0.5"
              :disabled="isSaving || !completionExternalAvailable || !remoteProvidersEnabled || selection !== 'allow'"
            >
            <span class="text-sm text-navy">
              <span class="font-semibold">Extern (OpenAI)</span>
              <span class="block text-xs text-navy/70">
                <template v-if="!completionExternalAvailable">Inte konfigurerad i den här miljön.</template>
                <template v-else-if="!remoteProvidersEnabled">
                  Systemadministratören tillåter inte externa AI-modeller i den här miljön.
                </template>
                <template v-else-if="selection !== 'allow'">
                  Aktivera Externa AI-API:er ovan för att kunna välja externa completions.
                </template>
                <template v-else>Använd externa completions när det är tillåtet.</template>
              </span>
            </span>
          </label>
        </fieldset>

        <div class="flex gap-2 pt-2">
          <button
            type="submit"
            class="btn-primary"
            :disabled="isSaving || (remoteProvidersEnabled && !selection)"
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
