<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { components } from "../../api/openapi";
import {
  buildSandboxDebugBundle,
  buildSandboxDebugJson,
  buildSandboxDebugText,
  getSandboxDebugState,
} from "../../composables/editor/sandboxDebugHelpers";
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

const isDebugOpen = ref(false);

const debugBundle = computed(() => {
  if (!displayedRun.value) return null;
  return buildSandboxDebugBundle(displayedRun.value);
});

const debugState = computed(() => {
  if (!displayedRun.value) {
    return { hasMissingDetails: true, hasNoOutput: false };
  }
  return getSandboxDebugState(displayedRun.value);
});

const debugJson = computed(() => (displayedRun.value ? buildSandboxDebugJson(displayedRun.value) : ""));
const debugText = computed(() => (displayedRun.value ? buildSandboxDebugText(displayedRun.value) : ""));

const stdoutValue = computed(() => debugBundle.value?.stdout ?? "null");
const stderrValue = computed(() => debugBundle.value?.stderr ?? "null");

const stdoutMeta = computed(() =>
  formatByteMeta(debugBundle.value?.stdout_bytes ?? null, debugBundle.value?.stdout_max_bytes ?? null),
);
const stderrMeta = computed(() =>
  formatByteMeta(debugBundle.value?.stderr_bytes ?? null, debugBundle.value?.stderr_max_bytes ?? null),
);
const stdoutTruncated = computed(() => debugBundle.value?.stdout_truncated === true);
const stderrTruncated = computed(() => debugBundle.value?.stderr_truncated === true);

watch(displayedRun, () => {
  isDebugOpen.value = false;
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

function formatByteMeta(bytes: number | null, maxBytes: number | null): string | null {
  if (bytes === null && maxBytes === null) return null;
  if (bytes === null && maxBytes !== null) return `Max ${maxBytes} bytes`;
  if (bytes !== null && maxBytes === null) return `${bytes} bytes`;
  return `${bytes} / ${maxBytes} bytes`;
}

async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "true");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

async function copyDebugJson(): Promise<void> {
  if (!displayedRun.value) return;
  await copyToClipboard(debugJson.value);
}

async function copyDebugText(): Promise<void> {
  if (!displayedRun.value) return;
  await copyToClipboard(debugText.value);
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

      <!-- Debug panel -->
      <div
        v-if="displayedRun"
        class="border border-navy bg-white shadow-brutal-sm"
      >
        <div class="flex flex-wrap items-center justify-between gap-3 px-3 py-2 border-b border-navy/20">
          <div>
            <h2 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
              Debug
            </h2>
            <p class="text-xs text-navy/60">
              Diagnostik för sandbox-körningen.
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="btn-primary"
              @click="copyDebugJson"
            >
              Kopiera debug (JSON)
            </button>
            <button
              type="button"
              class="btn-ghost"
              @click="copyDebugText"
            >
              Kopiera debug (text)
            </button>
            <button
              type="button"
              class="btn-ghost"
              @click="isDebugOpen = !isDebugOpen"
            >
              {{ isDebugOpen ? "Dölj" : "Visa" }}
            </button>
          </div>
        </div>

        <div
          v-if="isDebugOpen"
          class="border-t border-navy/20 bg-canvas/30 px-3 py-3 space-y-3"
        >
          <p
            v-if="debugState.hasMissingDetails"
            class="text-sm text-navy/70"
          >
            Debug-detaljer saknas för den här körningen.
          </p>
          <p
            v-else-if="debugState.hasNoOutput"
            class="text-sm text-navy/70 italic"
          >
            Ingen stdout/stderr för den här körningen.
          </p>
          <div
            v-else
            class="space-y-3"
          >
            <section class="space-y-1">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Stdout
                </h3>
                <span
                  v-if="stdoutMeta"
                  class="text-xs font-mono text-navy/60"
                >
                  {{ stdoutMeta }}
                </span>
                <span
                  v-if="stdoutTruncated"
                  class="px-2 py-0.5 text-xs font-semibold uppercase tracking-wide border border-warning text-warning"
                >
                  Trunkerad
                </span>
              </div>
              <pre
                class="border border-navy/20 bg-white p-2 text-xs font-mono whitespace-pre-wrap break-words"
                v-text="stdoutValue"
              />
            </section>

            <section class="space-y-1">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Stderr
                </h3>
                <span
                  v-if="stderrMeta"
                  class="text-xs font-mono text-navy/60"
                >
                  {{ stderrMeta }}
                </span>
                <span
                  v-if="stderrTruncated"
                  class="px-2 py-0.5 text-xs font-semibold uppercase tracking-wide border border-warning text-warning"
                >
                  Trunkerad
                </span>
              </div>
              <pre
                class="border border-navy/20 bg-white p-2 text-xs font-mono whitespace-pre-wrap break-words"
                v-text="stderrValue"
              />
            </section>
          </div>
        </div>
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
