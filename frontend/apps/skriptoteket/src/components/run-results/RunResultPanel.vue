<script setup lang="ts">
import { computed } from "vue";

import type { components } from "../../api/openapi";
import { UiActionForm } from "../ui-actions";
import { UiOutputRenderer } from "../ui-outputs";

type RunDetails = components["schemas"]["RunDetails"];
type RunStatus = components["schemas"]["RunStatus"];
type UiOutput = NonNullable<components["schemas"]["UiPayloadV2"]["outputs"]>[number];
type UiFormAction = components["schemas"]["UiFormAction"];

type SubmitPayload = {
  actionId: string;
  input: Record<string, components["schemas"]["JsonValue"]>;
};

const props = defineProps<{
  run: RunDetails;
  idBase: string;
  isSubmittingAction: boolean;
  canSubmitActions: boolean;
  actionErrorMessage: string | null;
}>();

const emit = defineEmits<{
  (e: "submit-action", payload: SubmitPayload): void;
}>();

function statusLabel(status: RunStatus): string {
  const labels: Record<RunStatus, string> = {
    running: "Pågår",
    succeeded: "Lyckades",
    failed: "Misslyckades",
    timed_out: "Tidsgräns",
  };
  return labels[status];
}

const outputs = computed<UiOutput[]>(() => props.run.ui_payload?.outputs ?? []);
const nextActions = computed<UiFormAction[]>(() => props.run.ui_payload?.next_actions ?? []);
const artifacts = computed(() => props.run.artifacts ?? []);

function onSubmitAction(payload: SubmitPayload): void {
  emit("submit-action", payload);
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3 text-sm text-navy/70">
      <span class="px-2 py-1 border border-navy bg-white shadow-brutal-sm font-semibold uppercase tracking-wide">
        {{ statusLabel(run.status) }}
      </span>
      <span class="font-mono text-xs text-navy/50">{{ run.run_id }}</span>
    </div>

    <div
      v-if="run.error_summary"
      class="p-4 border border-error bg-white shadow-brutal-sm text-error"
    >
      <p class="font-semibold">Ett fel uppstod</p>
      <pre class="mt-2 whitespace-pre-wrap font-mono text-xs">{{ run.error_summary }}</pre>
    </div>

    <div
      v-if="outputs.length > 0"
      class="space-y-3"
    >
      <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        Resultat
      </h2>
      <UiOutputRenderer
        v-for="(output, index) in outputs"
        :key="index"
        :output="output"
      />
    </div>

    <div
      v-if="nextActions.length > 0"
      class="space-y-3"
    >
      <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        Fortsätt
      </h2>

      <div
        v-if="actionErrorMessage"
        class="p-4 border border-error bg-white shadow-brutal-sm text-error text-sm"
      >
        {{ actionErrorMessage }}
      </div>

      <UiActionForm
        v-for="action in nextActions"
        :key="action.action_id"
        :action="action"
        :id-base="idBase"
        :disabled="isSubmittingAction || !canSubmitActions"
        @submit="onSubmitAction"
      />

      <p
        v-if="!canSubmitActions && !actionErrorMessage"
        class="text-xs text-navy/60"
      >
        Sessionen är inte redo än. Uppdatera och försök igen.
      </p>
    </div>

    <div
      v-if="artifacts.length > 0"
      class="space-y-2"
    >
      <h2 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        Filer
      </h2>

      <ul class="space-y-2">
        <li
          v-for="a in artifacts"
          :key="a.artifact_id"
          class="p-4 border border-navy bg-white shadow-brutal-sm flex items-center justify-between gap-4"
        >
          <div class="min-w-0">
            <a
              :href="a.download_url"
              class="underline text-burgundy hover:text-navy break-all"
              download
            >{{ a.path }}</a>
            <div class="text-xs text-navy/60">
              {{ a.bytes }} byte
            </div>
          </div>
          <span class="text-xs font-mono text-navy/50">{{ a.artifact_id }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

