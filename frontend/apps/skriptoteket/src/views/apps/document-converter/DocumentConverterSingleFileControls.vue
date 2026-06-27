<script setup lang="ts">
/**
 * File conversion source controls for the Document Converter route.
 *
 * Domain purpose:
 *   Let teachers choose between local upload and Mina filer, then submit a
 *   compatible file conversion without duplicating the route shell.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Displays options produced by `useDocumentConverterSingleFile`.
 *   - Emits user selections and submit intents back to the route host.
 */

import { ref } from "vue";

import { IconRefresh } from "../../../components/icons";
import {
  UiSegmentedToggle,
  type UiSegmentedToggleOption,
} from "../../../components/ui";
import type {
  DocumentConverterSavedFileSource,
} from "./documentConverterFileApi";
import type {
  DocumentConverterSingleFileOutput,
  DocumentConverterSingleFileSource,
} from "./useDocumentConverterSingleFile";

type SegmentedChoice = UiSegmentedToggleOption & {
  value: DocumentConverterSingleFileOutput | DocumentConverterSingleFileSource;
};

defineProps<{
  selectedOutputFormat: DocumentConverterSingleFileOutput;
  selectedSavedFileRef: string | null;
  selectedSourceAccept: string;
  selectedSourceFormat: DocumentConverterSingleFileSource;
  selectedSourceName: string;
  selectedFormatSummary: string;
  sourceMode: "upload" | "saved_file";
  isLoadingSources: boolean;
  isSubmitting: boolean;
  outputOptions: SegmentedChoice[];
  savedFiles: DocumentConverterSavedFileSource[];
  sourceOptions: SegmentedChoice[];
  sourceModeOptions: UiSegmentedToggleOption[];
}>();

const emit = defineEmits<{
  selectFiles: [files: File[]];
  selectOutputFormat: [value: DocumentConverterSingleFileOutput];
  selectSavedFile: [refValue: string | null];
  selectSourceFormat: [value: DocumentConverterSingleFileSource];
  selectSourceMode: [value: "upload" | "saved_file"];
  submit: [];
}>();

const fileInputElement = ref<HTMLInputElement | null>(null);

function openFilePicker(): void {
  fileInputElement.value?.click();
}

function onFileSelected(event: Event): void {
  const input = event.target as HTMLInputElement;
  emit("selectFiles", Array.from(input.files ?? []));
  input.value = "";
}
</script>

<template>
  <div class="dc-file-toolbar">
    <div class="dc-control-heading">
      <h2>Källa</h2>
      <span>{{ selectedFormatSummary }}</span>
    </div>

    <div class="dc-field">
      <UiSegmentedToggle
        :model-value="sourceMode"
        :options="sourceModeOptions"
        aria-label="Källa"
        variant="subrail"
        width="full"
        :columns="2"
        @update:model-value="(value) => emit('selectSourceMode', value as 'upload' | 'saved_file')"
      />
    </div>

    <div
      v-if="sourceMode === 'upload'"
      class="dc-dropzone"
      role="button"
      tabindex="0"
      @click="openFilePicker"
      @keydown.enter.prevent="openFilePicker"
      @keydown.space.prevent="openFilePicker"
    >
      <strong>Välj en fil som du vill konvertera</strong>
      <span>{{ selectedSourceName }}</span>
    </div>

    <div
      v-else
      class="dc-field"
    >
      <span>Mina filer</span>
      <select
        data-testid="document-converter-saved-file-select"
        :value="selectedSavedFileRef ?? ''"
        @change="emit('selectSavedFile', ($event.target as HTMLSelectElement).value || null)"
      >
        <option value="">
          Välj en fil
        </option>
        <option
          v-for="file in savedFiles"
          :key="file.ref"
          :value="file.ref"
        >
          {{ file.name }}
        </option>
      </select>
    </div>

    <input
      ref="fileInputElement"
      data-testid="document-converter-single-file-input"
      class="dc-file-input"
      type="file"
      multiple
      :accept="selectedSourceAccept"
      @change="onFileSelected"
    >
  </div>

  <section class="dc-control-section">
    <div class="dc-field">
      <span>Källformat</span>
      <UiSegmentedToggle
        :model-value="selectedSourceFormat"
        :options="sourceOptions"
        aria-label="Källformat"
        variant="subrail"
        width="full"
        :columns="Math.max(sourceOptions.length, 1)"
        @update:model-value="(value) => emit('selectSourceFormat', value as DocumentConverterSingleFileSource)"
      />
    </div>

    <div class="dc-field">
      <span>Exportformat</span>
      <UiSegmentedToggle
        :model-value="selectedOutputFormat"
        :options="outputOptions"
        aria-label="Exportformat"
        variant="subrail"
        width="full"
        :columns="Math.max(outputOptions.length, 1)"
        @update:model-value="(value) => emit('selectOutputFormat', value as DocumentConverterSingleFileOutput)"
      />
    </div>

    <button
      data-testid="document-converter-start-single-file"
      class="dc-neutral-button"
      type="button"
      :disabled="isSubmitting || isLoadingSources"
      @click="emit('submit')"
    >
      <IconRefresh :size="16" />
      {{ isSubmitting ? "Arbetar…" : "Skapa fil" }}
    </button>
  </section>
</template>
