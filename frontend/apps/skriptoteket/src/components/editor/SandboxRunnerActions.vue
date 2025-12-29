<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import { UiOutputRenderer } from "../ui-outputs";
import ToolRunActions from "../tool-run/ToolRunActions.vue";
import ToolRunArtifacts from "../tool-run/ToolRunArtifacts.vue";
import SystemMessage from "../ui/SystemMessage.vue";

type EditorRunDetails = components["schemas"]["EditorRunDetails"];
type RunStatus = components["schemas"]["RunStatus"];
type UiOutput = NonNullable<components["schemas"]["UiPayloadV2"]["outputs"]>[number];
type UiFormAction = NonNullable<components["schemas"]["UiPayloadV2"]["next_actions"]>[number];
type UiPayloadV2 = components["schemas"]["UiPayloadV2"];
type JsonValue = components["schemas"]["JsonValue"];

const props = defineProps<{
  runResult: EditorRunDetails | null;
  completedSteps: EditorRunDetails[];
  selectedStepIndex: number | null;
  isRunning: boolean;
  versionId: string;
  canSubmitActions: boolean;
  actionErrorMessage: string | null;
}>();

const emit = defineEmits<{
  (event: "select-step", index: number | null): void;
  (event: "submit-action", payload: { actionId: string; input: Record<string, JsonValue> }): void;
  (event: "update:actionErrorMessage", value: string | null): void;
}>();

const displayedRun = computed<EditorRunDetails | null>(() => {
  if (props.selectedStepIndex !== null) {
    return props.completedSteps[props.selectedStepIndex] ?? null;
  }
  return props.runResult;
});

const outputs = computed<UiOutput[]>(() => {
  const payload = displayedRun.value?.ui_payload as UiPayloadV2 | null;
  return payload?.outputs ?? [];
});

const artifacts = computed(() => displayedRun.value?.artifacts ?? []);

const nextActions = computed<UiFormAction[]>(() => {
  const payload = props.runResult?.ui_payload as UiPayloadV2 | null;
  return payload?.next_actions ?? [];
});

const actionIdBase = computed(
  () => `sandbox-${props.versionId}-${props.runResult?.run_id ?? "pending"}`
);

const actionError = computed({
  get: () => props.actionErrorMessage,
  set: (value) => emit("update:actionErrorMessage", value),
});

function statusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    running: "Kör...",
    succeeded: "Lyckades",
    failed: "Misslyckades",
    timed_out: "Tidsgräns",
  };
  return labels[status];
}
</script>

<template>
  <div class="space-y-4">
    <!-- Running state -->
    <div
      v-if="isRunning && runResult?.status === 'running'"
      class="flex items-center gap-2 text-sm text-navy/70"
    >
      <span class="inline-block w-4 h-4 border-2 border-navy/20 border-t-navy rounded-full animate-spin" />
      <span>Kör skriptet...</span>
    </div>

    <!-- Results -->
    <template v-if="runResult && runResult.status !== 'running'">
      <!-- Step history indicator -->
      <div
        v-if="completedSteps.length > 0"
        class="flex flex-wrap gap-2"
      >
        <button
          v-for="(step, index) in completedSteps"
          :key="step.run_id"
          type="button"
          class="btn-ghost btn-sm text-xs"
          :class="{ 'ring-2 ring-navy': selectedStepIndex === index }"
          @click="emit('select-step', index)"
        >
          Steg {{ index + 1 }}
        </button>
        <button
          type="button"
          class="btn-ghost btn-sm text-xs"
          :class="{ 'ring-2 ring-navy': selectedStepIndex === null }"
          @click="emit('select-step', null)"
        >
          Aktuellt
        </button>
      </div>

      <!-- Status row (uses displayedRun for viewing past steps) -->
      <div
        v-if="displayedRun"
        class="flex items-center gap-2 text-sm"
      >
        <span
          class="px-2 py-1 border font-semibold uppercase tracking-wide text-xs"
          :class="{
            'border-success bg-success/10 text-success': displayedRun.status === 'succeeded',
            'border-burgundy bg-burgundy/10 text-burgundy': displayedRun.status === 'failed',
            'border-warning bg-warning/10 text-warning': displayedRun.status === 'timed_out',
          }"
        >
          {{ statusLabel(displayedRun.status) }}
        </span>
        <span class="font-mono text-xs text-navy/50">
          {{ displayedRun.run_id.slice(0, 8) }}
        </span>
      </div>

      <!-- Error summary -->
      <div
        v-if="displayedRun?.error_summary"
        class="text-sm text-burgundy"
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

      <!-- Artifacts -->
      <ToolRunArtifacts :artifacts="artifacts" />

      <!-- Action error message -->
      <SystemMessage
        v-model="actionError"
        variant="error"
      />

      <!-- Next Actions (multi-step tools) - only show for current run -->
      <ToolRunActions
        v-if="nextActions.length > 0 && selectedStepIndex === null"
        :actions="nextActions"
        :id-base="actionIdBase"
        :disabled="!canSubmitActions"
        @submit="emit('submit-action', $event)"
      />
    </template>
  </div>
</template>
