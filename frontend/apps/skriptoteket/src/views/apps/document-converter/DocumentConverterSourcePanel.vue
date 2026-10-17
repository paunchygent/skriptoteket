<script setup lang="ts">
/**
 * Source panel for the Document Converter workspace.
 *
 * Domain purpose:
 *   Render the active source set for the selected Document Converter mode so
 *   teachers can choose project HTML entries or order local file conversions.
 *
 * Relationships:
 *   - Used only by `DocumentConverterView.vue`.
 *   - Displays state from the project-preview and file-conversion composables.
 *   - Emits source selection and ordering events back to the route host.
 */

import { UiGlyph } from "../../../components/ui/shared";

import { UiDenseActionButton } from "../../../components/ui";

type WorkspaceMode = "project_preview" | "single_file";

type AssetFile = {
  name: string;
};

defineProps<{
  workspaceMode: WorkspaceMode;
  projectCssFiles: AssetFile[];
  projectHtmlFiles: AssetFile[];
  projectImageFiles: AssetFile[];
  projectSelectedHtmlFilename: string | null;
  singleFileModeLabel: string;
  singleFileSavedFiles: AssetFile[];
  singleFileSourceName: string;
  singleFileUploadFiles: AssetFile[];
}>();

const emit = defineEmits<{
  moveSingleFileSavedFile: [fromIndex: number, toIndex: number];
  moveSingleFileUpload: [fromIndex: number, toIndex: number];
  removeSingleFileSavedFile: [index: number];
  removeSingleFileUpload: [index: number];
  selectProjectHtml: [filename: string];
}>();
</script>

<template>
  <div class="dc-source-panel">
    <section
      v-if="workspaceMode === 'project_preview'"
      class="dc-rail-section dc-assets"
    >
      <div class="dc-asset-heading">
        <h2>HTML ({{ projectHtmlFiles.length }}/10)</h2>
      </div>
      <button
        v-for="file in projectHtmlFiles"
        :key="file.name"
        class="dc-asset-row"
        :class="{ 'dc-asset-row--active': file.name === projectSelectedHtmlFilename }"
        type="button"
        @click="emit('selectProjectHtml', file.name)"
      >
        <UiGlyph
          meaning="document"
          :size="16"
          :stroke-width="2.25"
        />
        {{ file.name }}
      </button>

      <div class="dc-asset-heading dc-asset-heading--spaced">
        <h2>CSS ({{ projectCssFiles.length }}/10)</h2>
      </div>
      <div
        v-for="file in projectCssFiles"
        :key="file.name"
        class="dc-asset-row dc-asset-row--static"
      >
        <UiGlyph
          meaning="code-file"
          :size="16"
          :stroke-width="2.25"
        />
        {{ file.name }}
      </div>

      <div class="dc-asset-heading dc-asset-heading--spaced">
        <h2>Bilder ({{ projectImageFiles.length }}/20)</h2>
      </div>
      <div
        v-for="file in projectImageFiles"
        :key="file.name"
        class="dc-asset-row dc-asset-row--static"
      >
        <UiGlyph
          meaning="image-file"
          :size="16"
          :stroke-width="2.25"
        />
        {{ file.name }}
      </div>
    </section>

    <section
      v-else
      class="dc-rail-section dc-assets"
    >
      <p
        v-if="singleFileModeLabel === 'Lokal fil' && singleFileUploadFiles.length === 0"
        class="dc-source-empty"
      >
        Välj en fil som du vill konvertera.
      </p>

      <template v-else-if="singleFileModeLabel === 'Lokal fil'">
        <div
          v-for="(file, index) in singleFileUploadFiles"
          :key="file.name"
          class="dc-source-row"
        >
          <UiGlyph
            meaning="document"
            :size="16"
            :stroke-width="2.25"
          />
          <strong>{{ index + 1 }}. {{ file.name }}</strong>
          <div class="dc-source-row__actions">
            <UiDenseActionButton
              :data-testid="`document-converter-source-move-up-${index}`"
              label="Flytta upp"
              icon-only
              :disabled="index === 0"
              @click="emit('moveSingleFileUpload', index, index - 1)"
            >
              <template #leading>
                <UiGlyph
                  meaning="move-up"
                  :stroke-width="2.5"
                  :size="14"
                />
              </template>
            </UiDenseActionButton>
            <UiDenseActionButton
              :data-testid="`document-converter-source-move-down-${index}`"
              label="Flytta ned"
              icon-only
              :disabled="index === singleFileUploadFiles.length - 1"
              @click="emit('moveSingleFileUpload', index, index + 1)"
            >
              <template #leading>
                <UiGlyph
                  meaning="move-down"
                  :stroke-width="2.5"
                  :size="14"
                />
              </template>
            </UiDenseActionButton>
            <UiDenseActionButton
              :data-testid="`document-converter-source-remove-${index}`"
              label="Ta bort fil"
              icon-only
              @click="emit('removeSingleFileUpload', index)"
            >
              <template #leading>
                <UiGlyph
                  meaning="delete"
                  :size="14"
                  :stroke-width="2.5"
                />
              </template>
            </UiDenseActionButton>
          </div>
        </div>
      </template>

      <template v-else-if="singleFileModeLabel === 'Mina filer' && singleFileSavedFiles.length > 0">
        <div
          v-for="(file, index) in singleFileSavedFiles"
          :key="file.name"
          class="dc-source-row"
        >
          <UiGlyph
            meaning="document"
            :size="16"
            :stroke-width="2.25"
          />
          <strong>{{ index + 1 }}. {{ file.name }}</strong>
          <div class="dc-source-row__actions">
            <UiDenseActionButton
              :data-testid="`document-converter-source-move-up-${index}`"
              label="Flytta upp"
              icon-only
              :disabled="index === 0"
              @click="emit('moveSingleFileSavedFile', index, index - 1)"
            >
              <template #leading>
                <UiGlyph
                  meaning="move-up"
                  :stroke-width="2.5"
                  :size="14"
                />
              </template>
            </UiDenseActionButton>
            <UiDenseActionButton
              :data-testid="`document-converter-source-move-down-${index}`"
              label="Flytta ned"
              icon-only
              :disabled="index === singleFileSavedFiles.length - 1"
              @click="emit('moveSingleFileSavedFile', index, index + 1)"
            >
              <template #leading>
                <UiGlyph
                  meaning="move-down"
                  :stroke-width="2.5"
                  :size="14"
                />
              </template>
            </UiDenseActionButton>
            <UiDenseActionButton
              :data-testid="`document-converter-source-remove-${index}`"
              label="Ta bort fil"
              icon-only
              @click="emit('removeSingleFileSavedFile', index)"
            >
              <template #leading>
                <UiGlyph
                  meaning="delete"
                  :size="14"
                  :stroke-width="2.5"
                />
              </template>
            </UiDenseActionButton>
          </div>
        </div>
      </template>

      <div
        v-else
        class="dc-source-summary"
      >
        <UiGlyph
          meaning="document"
          :size="16"
          :stroke-width="2.25"
        />
        <strong>{{ singleFileSourceName }}</strong>
        <span>{{ singleFileModeLabel }}</span>
      </div>
    </section>
  </div>
</template>
