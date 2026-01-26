<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { storeToRefs } from "pinia";

import { useToast } from "../../composables/useToast";
import { useAiStore, type InlineCompletionProviderPreference, type RemoteFallbackPreference } from "../../stores/ai";

const ai = useAiStore();
const {
  remoteFallbackPreference,
  inlineCompletionProviderPreference,
  remoteProvidersEnabled,
  completionExternalAvailable,
  completionLocalAvailable,
} = storeToRefs(ai);
const toast = useToast();

// Single edit mode for entire section
const isEditing = ref(false);
const isSaving = ref(false);

// Local edit values
type RemoteFallbackSelection = Extract<RemoteFallbackPreference, "allow" | "deny"> | null;
type CompletionProviderSelection = Extract<InlineCompletionProviderPreference, "local" | "external">;

const remoteSelection = ref<RemoteFallbackSelection>(null);
const completionSelection = ref<CompletionProviderSelection>("local");

// Display values for collapsed state
const remoteDisplayValue = computed(() => {
  if (remoteFallbackPreference.value === "allow") return "Aktiverat";
  if (remoteFallbackPreference.value === "deny") return "Avstängt";
  return "Ej valt";
});

const completionDisplayValue = computed(() => {
  if (inlineCompletionProviderPreference.value === "external") return "Extern (OpenAI)";
  if (inlineCompletionProviderPreference.value === "local") return "Lokal (Devstral)";
  return completionLocalAvailable.value ? "Lokal (Devstral)" : "Extern (OpenAI)";
});

// External completion disabled logic
const externalCompletionDisabled = computed(() =>
  !completionExternalAvailable.value ||
  !remoteProvidersEnabled.value ||
  remoteSelection.value !== "allow"
);

// Start editing - populate both settings
function startEditing(): void {
  remoteSelection.value = remoteFallbackPreference.value === "unset" ? null : remoteFallbackPreference.value;
  if (inlineCompletionProviderPreference.value !== "unset") {
    completionSelection.value = inlineCompletionProviderPreference.value;
  } else {
    completionSelection.value = completionLocalAvailable.value ? "local" : "external";
  }
  isEditing.value = true;
}

function cancelEditing(): void {
  isEditing.value = false;
}

// Save both settings at once
async function saveSettings(): Promise<void> {
  if (isSaving.value) return;
  if (remoteProvidersEnabled.value && !remoteSelection.value) {
    toast.warning("Välj om du vill aktivera eller stänga av externa AI-API:er.");
    return;
  }

  isSaving.value = true;
  try {
    await ai.persistAiSettings({
      remote_fallback_preference: remoteProvidersEnabled.value ? remoteSelection.value ?? undefined : undefined,
      inline_completion_provider_preference: completionSelection.value,
    });
    toast.success("AI-inställningarna uppdaterades.");
    isEditing.value = false;
  } catch (error: unknown) {
    toast.failure(error instanceof Error ? error.message : "Kunde inte spara.");
  } finally {
    isSaving.value = false;
  }
}

// Auto-switch completion to local if remote fallback is denied
watch(remoteSelection, (sel) => {
  if (sel !== "allow" && completionSelection.value === "external") {
    completionSelection.value = "local";
  }
});

watch(remoteFallbackPreference, (pref) => {
  if (pref !== "allow" && inlineCompletionProviderPreference.value === "external") {
    void ai.persistInlineCompletionProviderPreference("local").catch(() => {});
  }
});

defineExpose({ startEditing, cancelEditing });
</script>

<template>
  <div>
    <!-- System admin restriction notice -->
    <div
      v-if="!remoteProvidersEnabled && !isEditing"
      class="py-2"
    >
      <div class="panel-inset-canvas p-2.5 text-xs text-navy/70">
        Systemadministratören tillåter inte externa AI-modeller i den här miljön.
      </div>
    </div>

    <!-- Read-only view -->
    <dl
      v-if="!isEditing"
      class="divide-y divide-navy/10"
    >
      <div class="ai-setting-row">
        <dt class="ai-setting-label">Externa AI-API:er</dt>
        <dd class="ai-setting-value">{{ remoteDisplayValue }}</dd>
      </div>
      <div class="ai-setting-row">
        <dt class="ai-setting-label">Completions</dt>
        <dd class="ai-setting-value">{{ completionDisplayValue }}</dd>
      </div>
    </dl>

    <!-- Edit form -->
    <div
      v-else
      class="ai-edit-form"
    >
      <!-- External AI APIs -->
      <fieldset class="ai-fieldset">
        <legend class="ai-fieldset-legend">Externa AI-API:er</legend>
        <div class="space-y-2">
          <label class="radio-option-card">
            <input
              v-model="remoteSelection"
              type="radio"
              name="remote-fallback"
              value="allow"
              class="mt-0.5"
              :disabled="isSaving || !remoteProvidersEnabled"
            >
            <span class="text-sm text-navy">
              <span class="font-semibold">Aktivera</span>
              <span class="block text-xs text-navy/70">
                Kodassistenten kan använda externa API:er om lokala modeller är nere.
              </span>
            </span>
          </label>
          <label class="radio-option-card">
            <input
              v-model="remoteSelection"
              type="radio"
              name="remote-fallback"
              value="deny"
              class="mt-0.5"
              :disabled="isSaving || !remoteProvidersEnabled"
            >
            <span class="text-sm text-navy">
              <span class="font-semibold">Stäng av</span>
              <span class="block text-xs text-navy/70">
                Endast lokala modeller.
              </span>
            </span>
          </label>
        </div>
      </fieldset>

      <!-- Completions -->
      <fieldset class="ai-fieldset">
        <legend class="ai-fieldset-legend">Completions</legend>
        <div class="space-y-2">
          <label
            class="radio-option-card"
            :class="{ 'radio-option-card--disabled': !completionLocalAvailable }"
          >
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
                {{ completionLocalAvailable ? 'Kör via lokala modeller.' : 'Inte tillgänglig.' }}
              </span>
            </span>
          </label>
          <label
            class="radio-option-card"
            :class="{ 'radio-option-card--disabled': externalCompletionDisabled }"
          >
            <input
              v-model="completionSelection"
              type="radio"
              name="completion-provider"
              value="external"
              class="mt-0.5"
              :disabled="isSaving || externalCompletionDisabled"
            >
            <span class="text-sm text-navy">
              <span class="font-semibold">Extern (OpenAI)</span>
              <span class="block text-xs text-navy/70">
                <template v-if="externalCompletionDisabled && remoteSelection !== 'allow'">
                  Aktivera externa API:er först.
                </template>
                <template v-else>
                  Använd externa completions.
                </template>
              </span>
            </span>
          </label>
        </div>
      </fieldset>

      <!-- Actions -->
      <div class="ai-form-actions">
        <button
          type="button"
          class="btn-inline-primary"
          :disabled="isSaving || (remoteProvidersEnabled && !remoteSelection)"
          @click="saveSettings"
        >
          {{ isSaving ? 'Sparar...' : 'Spara ändringar' }}
        </button>
        <button
          type="button"
          class="btn-inline-cancel"
          :disabled="isSaving"
          @click="cancelEditing"
        >
          Avbryt
        </button>
      </div>
    </div>

    <!-- Footer note -->
    <div
      v-if="!isEditing"
      class="pt-2"
    >
      <p class="text-[10px] text-navy/50 leading-relaxed">
        Externa AI-API:er kan skicka innehåll utanför servern.
      </p>
    </div>
  </div>
</template>

<style scoped>
/* Row layout: 2-column grid for read-only view */
.ai-setting-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.25rem;
  padding: 0.5rem 0;
  align-items: center;
}

@media (min-width: 640px) {
  .ai-setting-row {
    grid-template-columns: 11rem 1fr;
    gap: 1rem;
  }
}

.ai-setting-label {
  font-size: var(--huleedu-text-xs, 0.75rem);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--huleedu-navy-70, rgba(26, 43, 60, 0.7));
}

.ai-setting-value {
  font-size: var(--huleedu-text-sm, 0.875rem);
  color: var(--huleedu-navy, #1a2b3c);
}

/* Edit form */
.ai-edit-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.5rem 0;
}

.ai-fieldset {
  border: none;
  padding: 0;
  margin: 0;
}

.ai-fieldset-legend {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(26, 43, 60, 0.6);
  margin-bottom: 0.5rem;
}

.ai-form-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(26, 43, 60, 0.1);
}
</style>
