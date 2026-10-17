<script setup lang="ts">
import type { components } from "../../api/openapi";
import { UiDenseActionButton } from "../ui";
import type { ToolInputFormValues } from "../../composables/tools/useToolInputs";
import type { FileFieldSelection, FileSelectionMode, ToolFileFieldSpec } from "../../composables/tools/useToolInputs";
import type { FileRefInfo } from "../../composables/tools/fileRefHelpers";
import ToolInputForm from "../tool-run/ToolInputForm.vue";
import ToolFileFieldPicker from "../tool-run/ToolFileFieldPicker.vue";

type CreateDraftVersionRequest = components["schemas"]["CreateDraftVersionRequest"];
type ToolInputSchema = NonNullable<CreateDraftVersionRequest["input_schema"]>;
type ToolInputField = ToolInputSchema[number];

defineProps<{
  idBase: string;
  inputFields: ToolInputField[];
  inputValues: ToolInputFormValues;
  inputFieldErrors: Record<string, string>;
  inputSchemaError: string | null;
  inputsPreview: string;
  fileFields: ToolFileFieldSpec[];
  fileSelections: Record<string, FileFieldSelection>;
  fileAcceptByField: Record<string, string | undefined>;
  fileErrors: Record<string, string | null>;
  availableFileRefs: FileRefInfo[];
  isRunning: boolean;
  isReadOnly: boolean;
  hasResults: boolean;
  canRun: boolean;
}>();

const emit = defineEmits<{
  (event: "update:inputValues", value: ToolInputFormValues): void;
  (event: "update:fileMode", value: { field: string; mode: FileSelectionMode }): void;
  (event: "update:fileUploads", value: { field: string; files: File[] }): void;
  (event: "update:fileRefs", value: { field: string; refs: string[] }): void;
  (event: "delete:fileRefs", value: { field: string; refs: string[] }): void;
  (event: "run"): void;
  (event: "clear"): void;
}>();

function updateInputValues(value: ToolInputFormValues): void {
  emit("update:inputValues", value);
}
</script>

<template>
  <div class="max-w-[min(960px,100%)] space-y-4">
    <div v-if="inputFields.length > 0">
      <ToolInputForm
        :id-base="idBase"
        :fields="inputFields"
        :model-value="inputValues"
        :errors="inputFieldErrors"
        density="compact"
        @update:model-value="updateInputValues"
      />
    </div>

    <p
      v-if="inputSchemaError"
      class="text-xs font-semibold text-critical"
    >
      {{ inputSchemaError }}
    </p>

    <ToolFileFieldPicker
      v-if="fileFields.length > 0"
      :fields="fileFields"
      :selections="fileSelections"
      :accept-by-field="fileAcceptByField"
      :errors="fileErrors"
      :available-refs="availableFileRefs"
      density="compact"
      :is-read-only="isReadOnly"
      @update:mode="emit('update:fileMode', $event)"
      @update:uploads="emit('update:fileUploads', $event)"
      @update:refs="emit('update:fileRefs', $event)"
      @delete:refs="emit('delete:fileRefs', $event)"
    />

    <div class="flex flex-wrap gap-2">
      <UiDenseActionButton
        label="Testkör kod"
        :disabled="!canRun || isRunning || isReadOnly"
        :busy="isRunning"
        class="min-w-[120px]"
        @click="emit('run')"
      />

      <UiDenseActionButton
        v-if="hasResults"
        label="Rensa"
        @click="emit('clear')"
      />
    </div>

    <details class="panel-inset">
      <summary class="px-3 py-2 cursor-pointer text-xs font-semibold uppercase tracking-wide text-navy/70">
        Indata (JSON)
      </summary>
      <div class="px-3 py-2 border-t border-navy/20 bg-canvas/30 space-y-2">
        <p class="text-xs text-navy/60">
          Skickas som <span class="font-mono">SKRIPTOTEKET_INPUTS</span>.
        </p>
        <pre class="whitespace-pre-wrap font-mono text-xs text-navy">{{ inputsPreview }}</pre>
      </div>
    </details>
  </div>
</template>
