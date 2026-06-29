<script setup lang="ts">
/**
 * Source intake controls for the Document Converter workspace.
 *
 * Domain purpose:
 *   Keep project and single-file picker/drop controls at the top of the
 *   source column so file intake remains separate from output operations.
 *
 * Relationships:
 *   - Used by `DocumentConverterView.vue`.
 *   - Emits selected project events and single-file source selections back to
 *     the route host.
 *   - Leaves source lists to `DocumentConverterSourcePanel.vue`.
 */

import { ref } from "vue";

import {
  UiSegmentedToggle,
  type UiSegmentedToggleOption,
} from "../../../components/ui";
import type { DocumentConverterSavedFileSource } from "./documentConverterFileApi";

type WorkspaceMode = "project_preview" | "single_file";

defineProps<{
  selectedSavedFileRef: string | null;
  selectedSourceAccept: string;
  selectedSourceName: string;
  sourceMode: "upload" | "saved_file";
  sourceModeOptions: UiSegmentedToggleOption[];
  savedFiles: DocumentConverterSavedFileSource[];
  workspaceMode: WorkspaceMode;
}>();

const emit = defineEmits<{
  projectFilesDropped: [event: DragEvent];
  projectFilesSelected: [event: Event];
  selectSavedFile: [refValue: string | null];
  selectSingleFiles: [files: File[]];
  selectSourceMode: [value: "upload" | "saved_file"];
}>();

const projectFileInputElement = ref<HTMLInputElement | null>(null);
const singleFileInputElement = ref<HTMLInputElement | null>(null);

function openProjectFilePicker(): void {
  projectFileInputElement.value?.click();
}

function openSingleFilePicker(): void {
  singleFileInputElement.value?.click();
}

function onSingleFileSelected(event: Event): void {
  const input = event.target as HTMLInputElement;
  emit("selectSingleFiles", Array.from(input.files ?? []));
  input.value = "";
}
</script>

<template>
  <div class="dc-source-intake">
    <template v-if="workspaceMode === 'project_preview'">
      <div
        data-testid="document-converter-dropzone"
        class="dc-dropzone"
        role="button"
        tabindex="0"
        @click="openProjectFilePicker"
        @keydown.enter.prevent="openProjectFilePicker"
        @keydown.space.prevent="openProjectFilePicker"
        @dragover.prevent
        @drop="emit('projectFilesDropped', $event)"
      >
        <strong>Dra filer hit eller klicka</strong>
        <span>HTML, CSS och bilder</span>
      </div>
      <input
        ref="projectFileInputElement"
        data-testid="document-converter-file-input"
        class="dc-file-input"
        type="file"
        multiple
        accept=".html,.htm,.css,.png,.jpg,.jpeg,.webp"
        @change="emit('projectFilesSelected', $event)"
      >
    </template>

    <section
      v-else
      class="dc-source-picker"
    >
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
        @click="openSingleFilePicker"
        @keydown.enter.prevent="openSingleFilePicker"
        @keydown.space.prevent="openSingleFilePicker"
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
        ref="singleFileInputElement"
        data-testid="document-converter-single-file-input"
        class="dc-file-input"
        type="file"
        multiple
        :accept="selectedSourceAccept"
        @change="onSingleFileSelected"
      >
    </section>
  </div>
</template>
