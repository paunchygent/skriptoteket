<script setup lang="ts">
/**
 * File conversion source controls for the Document Converter route.
 *
 * Domain purpose:
 *   Let teachers choose compatible source and export formats, then submit a
 *   file conversion inside the shared Document Converter operations column.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Displays options produced by `useDocumentConverterSingleFile`.
 *   - Emits user selections and submit intents back to the route host.
 */

import { IconRefresh } from "../../../components/icons";
import {
  UiSegmentedToggle,
  type UiSegmentedToggleOption,
} from "../../../components/ui";
import type {
  DocumentConverterSingleFileOutput,
  DocumentConverterSingleFileSource,
} from "./useDocumentConverterSingleFile";

type SegmentedChoice = UiSegmentedToggleOption & {
  value: DocumentConverterSingleFileOutput | DocumentConverterSingleFileSource;
};

defineProps<{
  selectedOutputFormat: DocumentConverterSingleFileOutput;
  selectedSourceFormat: DocumentConverterSingleFileSource;
  isLoadingSources: boolean;
  isSubmitting: boolean;
  outputOptions: SegmentedChoice[];
  sourceOptions: SegmentedChoice[];
}>();

const emit = defineEmits<{
  selectOutputFormat: [value: DocumentConverterSingleFileOutput];
  selectSourceFormat: [value: DocumentConverterSingleFileSource];
  submit: [];
}>();
</script>

<template>
  <section class="dc-operations-section">
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
