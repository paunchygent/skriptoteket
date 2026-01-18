<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import type { components } from "../api/openapi";
import { UiOutputRenderer } from "../components/ui-outputs";
import ToolInputForm from "../components/tool-run/ToolInputForm.vue";
import ToolRunActions from "../components/tool-run/ToolRunActions.vue";
import ToolRunArtifacts from "../components/tool-run/ToolRunArtifacts.vue";
import ToolRunControlBar from "../components/tool-run/ToolRunControlBar.vue";
import SessionFilesPanel from "../components/tool-run/SessionFilesPanel.vue";
import UsageInstructions from "../components/tool-run/UsageInstructions.vue";
import ToolRunSettingsPanel from "../components/tool-run/ToolRunSettingsPanel.vue";
import ToolRunStepIndicator from "../components/tool-run/ToolRunStepIndicator.vue";
import SystemMessage from "../components/ui/SystemMessage.vue";
import { useToolRun, type StepResult } from "../composables/tools/useToolRun";
import { useToolSettings } from "../composables/tools/useToolSettings";

type UiOutput = NonNullable<components["schemas"]["UiPayloadV2"]["outputs"]>[number];
type UiFormAction = components["schemas"]["UiFormAction"];
type RunStatus = components["schemas"]["RunStatus"];

const route = useRoute();

const slug = computed(() => {
  const param = route.params.slug;
  return typeof param === "string" ? param : "";
});

const {
  tool,
  selectedFiles,
  inputValues,
  inputFields,
  inputFieldErrors,
  fileField,
  fileAccept,
  fileLabel,
  fileMultiple,
  fileError,
  sessionFiles,
  sessionFilesMode,
  sessionFilesHelperText,
  currentRun,
  completedSteps,
  isLoadingTool,
  isSubmitting,
  isRunning,
  errorMessage,
  actionErrorMessage,
  hasResults,
  hasNextActions,
  canSubmitActions,
  canSubmitRun,
  canReuseSessionFiles,
  canClearSessionFiles,
  loadTool,
  submitRun,
  submitAction,
  clearRun,
  selectFiles,
} = useToolRun({ slug });

const toolId = computed(() => tool.value?.id ?? "");
const {
  settingsSchema,
  values: settingsValues,
  hasSchema: hasSettingsSchema,
  isLoading: isLoadingSettings,
  isSaving: isSavingSettings,
  errorMessage: settingsErrorMessage,
  saveSettings,
} = useToolSettings({ toolId });

const isSettingsOpen = ref(false);

const selectedStepRun = ref<StepResult | null>(null);
const displayedRun = computed(() => selectedStepRun.value?.run ?? currentRun.value);

const allSteps = computed<StepResult[]>(() => {
  const steps = [...completedSteps.value];
  if (currentRun.value) {
    // Determine if this is a terminal step (no more actions to take)
    const isTerminal = ["succeeded", "failed", "timed_out", "cancelled"].includes(
      currentRun.value.status,
    );
    const hasActions = (currentRun.value.ui_payload?.next_actions?.length ?? 0) > 0;

    steps.push({
      id: currentRun.value.run_id,
      stepNumber: completedSteps.value.length + 1,
      label: `Steg ${completedSteps.value.length + 1}`,
      status: isTerminal && !hasActions ? "completed" : "current",
      run: currentRun.value,
    });
  }
  return steps;
});

const currentStepNumber = computed(() => completedSteps.value.length + 1);
const showStepIndicator = computed(() => completedSteps.value.length > 0 || hasNextActions.value);
const idBase = computed(() => `tool-${slug.value}-run-${displayedRun.value?.run_id ?? "none"}`);

const outputs = computed<UiOutput[]>(() => displayedRun.value?.ui_payload?.outputs ?? []);
const nextActions = computed<UiFormAction[]>(() => displayedRun.value?.ui_payload?.next_actions ?? []);
const artifacts = computed(() => displayedRun.value?.artifacts ?? []);

function onToggleSettings(): void {
  isSettingsOpen.value = !isSettingsOpen.value;
}

function onSettingsValuesUpdate(next: Record<string, string | boolean | string[]>): void {
  settingsValues.value = next;
}

function onInputValuesUpdate(next: Record<string, string | boolean>): void {
  inputValues.value = next;
}

function statusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    queued: "Köad",
    running: "Pågår",
    succeeded: "Lyckades",
    failed: "Misslyckades",
    timed_out: "Tidsgräns",
    cancelled: "Avbruten",
  };
  return labels[status] ?? status;
}

function onFilesSelected(files: File[]): void {
  selectFiles(files);
}

function onRun(): void {
  selectedStepRun.value = null;
  void submitRun();
}

function onClear(): void {
  selectedStepRun.value = null;
  clearRun();
}

function onSelectStep(step: StepResult): void {
  selectedStepRun.value = step;
}

function onSubmitAction(payload: {
  actionId: string;
  input: Record<string, components["schemas"]["JsonValue"]>;
}): void {
  selectedStepRun.value = null;
  void submitAction(payload);
}

watch(currentRun, () => {
  selectedStepRun.value = null;
});

onMounted(() => {
  void loadTool();
});

watch(slug, () => {
  clearRun();
  void loadTool();
});

watch(toolId, () => {
  isSettingsOpen.value = false;
});

watch(hasSettingsSchema, (hasSchema) => {
  if (!hasSchema) {
    isSettingsOpen.value = false;
  }
});
</script>

<template>
  <div class="max-w-3xl space-y-6">
    <RouterLink
      to="/browse"
      class="text-sm text-navy/70 underline hover:text-burgundy"
    >
      {{ "\u2190" }} Tillbaka till katalog
    </RouterLink>

    <div class="space-y-2">
      <h1 class="page-title">{{ tool?.title ?? (isLoadingTool ? "Laddar..." : "Okänt verktyg") }}</h1>
      <p
        v-if="tool?.summary"
        class="text-navy/60"
      >
        {{ tool.summary }}
      </p>
    </div>

    <div
      v-if="isLoadingTool"
      class="p-4 border border-navy bg-white shadow-brutal-sm text-navy/70 text-sm"
    >
      Laddar...
    </div>

    <SystemMessage
      v-else-if="errorMessage && !tool"
      v-model="errorMessage"
      variant="error"
    />

    <!-- UNIFIED TOOL CARD -->
    <div
      v-else-if="tool"
      class="border border-navy bg-white shadow-brutal-sm"
    >
      <UsageInstructions
        v-if="tool.usage_instructions?.trim()"
        :tool-id="tool.id"
        :instructions="tool.usage_instructions"
        :is-seen="tool.usage_instructions_seen"
      />

      <!-- Control bar section -->
      <div class="p-4 border-b border-navy/20">
        <ToolInputForm
          v-if="inputFields.length > 0"
          :id-base="`${idBase}-prerun`"
          :fields="inputFields"
          :model-value="inputValues"
          :errors="inputFieldErrors"
          class="mb-4"
          @update:model-value="onInputValuesUpdate"
        />

        <ToolRunControlBar
          :selected-files="selectedFiles"
          :is-running="isSubmitting || isRunning"
          :has-results="hasResults"
          :has-settings="hasSettingsSchema"
          :is-settings-open="isSettingsOpen"
          :show-file-picker="fileField !== null"
          :file-label="fileLabel"
          :file-accept="fileAccept"
          :file-multiple="fileMultiple"
          :file-error="fileError"
          :can-run="canSubmitRun"
          @files-selected="onFilesSelected"
          @run="onRun"
          @clear="onClear"
          @toggle-settings="onToggleSettings"
        />

        <div class="mt-4">
          <SessionFilesPanel
            v-model:mode="sessionFilesMode"
            :files="sessionFiles"
            :can-reuse="canReuseSessionFiles"
            :can-clear="canClearSessionFiles"
            :helper-text="sessionFilesHelperText"
          />
        </div>
      </div>

      <div
        v-if="isSettingsOpen && hasSettingsSchema && settingsSchema"
        class="px-4 py-4 border-b border-navy/20 bg-canvas/30"
      >
        <ToolRunSettingsPanel
          v-model:error-message="settingsErrorMessage"
          :id-base="idBase"
          :schema="settingsSchema"
          :model-value="settingsValues"
          :is-loading="isLoadingSettings"
          :is-saving="isSavingSettings"
          @update:model-value="onSettingsValuesUpdate"
          @save="saveSettings"
        />
      </div>

      <!-- Step indicator (if multi-step) -->
      <div
        v-if="showStepIndicator"
        class="px-4 py-3 border-b border-navy/20 bg-canvas/50"
      >
        <ToolRunStepIndicator
          :steps="allSteps"
          :current-step-number="currentStepNumber"
          @select-step="onSelectStep"
        />
      </div>

      <!-- Error message -->
      <div
        v-if="errorMessage"
        class="px-4 py-3 border-b border-navy/20 bg-white"
      >
        <SystemMessage
          v-model="errorMessage"
          variant="error"
          class="shadow-none"
        />
      </div>

      <!-- Running state -->
      <div
        v-if="(isSubmitting && !displayedRun) || displayedRun?.status === 'running' || displayedRun?.status === 'queued'"
        class="px-4 py-3 flex items-center gap-2 text-navy/70 text-sm"
      >
        <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
        <span>{{ displayedRun?.status === "queued" ? "Köar..." : "Kör..." }}</span>
      </div>

      <!-- Results section -->
      <template v-if="displayedRun && displayedRun.status !== 'running' && displayedRun.status !== 'queued'">
        <div class="p-4 space-y-4">
          <!-- Viewing past step notice -->
          <div
            v-if="selectedStepRun"
            class="text-xs text-navy/60"
          >
            Visar resultat för {{ selectedStepRun.label }}.
            <button
              type="button"
              class="underline hover:text-burgundy"
              @click="selectedStepRun = null"
            >
              Visa aktuellt
            </button>
          </div>

          <!-- Status row -->
          <div class="flex items-center gap-2 text-sm">
            <span class="px-2 py-1 border border-navy font-semibold uppercase tracking-wide text-xs">
              {{ statusLabel(displayedRun.status) }}
            </span>
            <span class="font-mono text-xs text-navy/50">
              {{ displayedRun.run_id.slice(0, 8) }}
            </span>
          </div>

          <!-- Error summary -->
          <div
            v-if="displayedRun.error_summary"
            class="text-sm text-error"
          >
            <p class="font-semibold">Ett fel uppstod</p>
            <pre class="mt-1 whitespace-pre-wrap font-mono text-xs">{{ displayedRun.error_summary }}</pre>
          </div>

          <!-- Outputs -->
          <div
            v-if="outputs.length > 0"
            class="space-y-3"
          >
            <UiOutputRenderer
              v-for="(output, index) in outputs"
              :key="index"
              :output="output"
            />
          </div>

          <!-- Actions -->
          <ToolRunActions
            v-if="nextActions.length > 0 && !selectedStepRun"
            v-model:error-message="actionErrorMessage"
            :actions="nextActions"
            :id-base="idBase"
            :disabled="isSubmitting || !canSubmitActions"
            @submit="onSubmitAction"
          />

          <!-- Artifacts -->
          <ToolRunArtifacts :artifacts="artifacts" />
        </div>
      </template>

      <!-- Empty state when no run yet -->
      <div
        v-else-if="!isSubmitting && !displayedRun"
        class="px-4 py-6 text-center text-navy/50 text-sm"
      >
        Välj filer och klicka Kör för att starta.
      </div>
    </div>
  </div>
</template>
