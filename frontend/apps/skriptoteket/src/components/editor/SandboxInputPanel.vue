<script setup lang="ts">
import type { components } from "../../api/openapi";
import type { ToolInputFormValues } from "../../composables/tools/useToolInputs";
import ToolInputForm from "../tool-run/ToolInputForm.vue";

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
  selectedFiles: File[];
  showFilePicker: boolean;
  fileLabel: string;
  fileAccept?: string;
  fileMultiple: boolean;
  fileError: string | null;
  isRunning: boolean;
  isReadOnly: boolean;
  hasResults: boolean;
  canRun: boolean;
}>();

const emit = defineEmits<{
  (event: "update:inputValues", value: ToolInputFormValues): void;
  (event: "update:selectedFiles", value: File[]): void;
  (event: "run"): void;
  (event: "clear"): void;
}>();

function onFilesSelected(event: Event): void {
  const target = event.target as HTMLInputElement;
  if (target.files) {
    emit("update:selectedFiles", Array.from(target.files));
  }
}

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
      class="text-xs font-semibold text-burgundy"
    >
      {{ inputSchemaError }}
    </p>

    <div class="space-y-2">
      <label
        v-if="showFilePicker"
        class="block text-[10px] font-semibold uppercase tracking-wide text-navy/60"
      >
        {{ fileLabel }}
      </label>

      <!-- Input + buttons row (same height via items-stretch) -->
      <div class="flex flex-col gap-2 sm:flex-row sm:items-stretch">
        <div
          v-if="showFilePicker"
          class="flex-1 min-w-0"
        >
          <div
            class="flex items-center gap-2 w-full h-[28px] border border-navy/30 bg-white px-2.5 shadow-none overflow-hidden"
          >
            <label
              class="btn-ghost shrink-0 h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
              :class="{ 'opacity-60 pointer-events-none': isReadOnly }"
            >
              Välj filer
              <input
                type="file"
                :multiple="fileMultiple"
                :accept="fileAccept"
                class="sr-only"
                :disabled="isReadOnly"
                @change="onFilesSelected"
              >
            </label>
            <span class="text-[11px] text-navy/60 truncate">
              {{ selectedFiles.length > 0 ? `${selectedFiles.length} fil(er) valda` : "Inga filer valda" }}
            </span>
          </div>
        </div>

        <button
          type="button"
          :disabled="!canRun || isRunning || isReadOnly"
          class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none min-w-[120px]"
          @click="emit('run')"
        >
          <span
            v-if="isRunning"
            class="inline-block w-3 h-3 border-2 border-navy/20 border-t-navy rounded-full animate-spin"
          />
          <span v-else>Testkör kod</span>
        </button>

        <button
          v-if="hasResults"
          type="button"
          class="btn-ghost h-[28px] px-2.5 py-1 text-[10px] font-semibold normal-case tracking-[var(--huleedu-tracking-label)] shadow-none border-navy/30 bg-canvas leading-none"
          @click="emit('clear')"
        >
          Rensa
        </button>
      </div>

      <p
        v-if="showFilePicker && fileError"
        class="text-xs font-semibold text-burgundy"
      >
        {{ fileError }}
      </p>
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
