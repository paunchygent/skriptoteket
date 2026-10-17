<script setup lang="ts">
/**
 * Roster create/edit modal.
 *
 * This modal owns the CRUD surface for reusable class lists used by the
 * classroom planner. Import-from-file now lives inside the same workflow so
 * teachers can start from a Skola24 export, review the parsed result, and only
 * fall back to manual edits when the parser needs help.
 */

import { nextTick, ref } from "vue";
import { IconTrash } from "../../../components/icons";
import { SystemMessage, UiDenseIconButton, UiGlyph } from "../../../components/ui";
import type { Roster, Student } from "../classroomPlannerTypes";
import { useRosterForm } from "./useRosterForm";
import { useRosterImport } from "./useRosterImport";

const props = defineProps<{
  roster?: Roster | null;
  importPreviewApiPath?: string;
  saveRoster?: (payload: {
    existingRoster: Roster | null;
    name: string;
    students: Student[];
  }) => Promise<Roster>;
  deleteRoster?: (rosterId: string) => Promise<void>;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "saved", roster: Roster): void;
  (e: "deleted", rosterId: string): void;
}>();

const form = useRosterForm(props, {
  saved: (roster) => emit("saved", roster),
  deleted: (rosterId) => emit("deleted", rosterId),
});
const {
  name, rawStudents, isSubmitting, isDeleting, formError,
  isEditing, parsedStudents, isValid, submit, removeRoster,
} = form;
const {
  fileInput, ambiguousRows, isImportDropActive, isUploading, preview, importError,
  importDropZoneClass, resetImport, triggerFileInput, onFileSelected,
  onImportDragEnter, onImportDragOver, onImportDragLeave, onImportDrop,
  appendAmbiguousRow, dismissAmbiguousRow,
} = useRosterImport({ apiPath: props.importPreviewApiPath, roster: () => props.roster }, form);
const importTrigger = ref<HTMLButtonElement | null>(null);

async function updateImportError(value: string | null): Promise<void> {
  importError.value = value;
  if (value === null) {
    await nextTick();
    importTrigger.value?.focus();
  }
}

function closeModal(): void {
  resetImport();
  emit("close");
}
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto p-4">
    <button
      type="button"
      aria-label="Stäng modal"
      class="planner-overlay-backdrop"
      @click="closeModal"
    />
    <div class="relative flex min-h-full items-start justify-center py-4">
      <div
        class="flex max-h-[calc(100vh-2rem)] w-full max-w-2xl flex-col border border-navy bg-modal shadow-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby="roster-modal-title"
        data-test="roster-modal-shell"
      >
        <div class="flex items-start justify-between gap-4 border-b border-navy/20 pb-4">
          <div class="min-w-0 space-y-1 px-6 pt-6 md:px-8 md:pt-8">
            <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Klasslistor
            </p>
            <h2
              id="roster-modal-title"
              class="font-sans text-2xl text-navy"
            >
              {{ isEditing ? "Redigera klasslista" : "Ny klasslista" }}
            </h2>
          </div>
          <UiDenseIconButton
            label="Stäng"
            class="mr-6 mt-6 md:mr-8 md:mt-8"
            @click="closeModal"
          >
            <UiGlyph
              meaning="close"
              :size="14"
            />
          </UiDenseIconButton>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-6 pb-6 pt-4 md:px-8 md:pb-8">
          <SystemMessage
            v-if="formError"
            v-model="formError"
            tone="failure"
            dismissible
            role="alert"
            aria-live="assertive"
            aria-atomic="true"
          />

          <div class="mt-6 space-y-5">
            <section class="space-y-3 border border-navy/20 bg-canvas p-4">
              <input
                ref="fileInput"
                type="file"
                class="hidden"
                accept=".xlsx,.xls,.csv,.tsv,.txt,.pdf"
                @change="onFileSelected"
              >

              <div class="space-y-1">
                <p class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Importera från fil
                </p>
                <p class="text-sm leading-relaxed text-navy/75">
                  Börja gärna med en Skola24-klasslista eller grupplista i Excel
                  (`.xls`), PDF eller text (`.txt`). Även `.csv` och `.tsv` stöds.
                </p>
              </div>

              <div
                class="flex flex-col items-center gap-3 border border-dashed px-4 py-5 text-center transition-colors"
                :class="importDropZoneClass"
                :aria-busy="isUploading ? 'true' : 'false'"
                data-test="roster-modal-import-dropzone"
                @dragenter="onImportDragEnter"
                @dragover="onImportDragOver"
                @dragleave="onImportDragLeave"
                @drop="onImportDrop"
              >
                <p class="text-sm font-semibold uppercase tracking-[var(--huleedu-tracking-label)]">
                  {{ isImportDropActive ? "Släpp filen här" : "Dra och släpp filen här" }}
                </p>
                <p class="max-w-md text-sm leading-relaxed">
                  Dra och släpp filen här, eller klicka på knappen för att välja fil.
                </p>
                <button
                  ref="importTrigger"
                  type="button"
                  class="btn-primary shrink-0"
                  data-test="roster-modal-import-trigger"
                  :disabled="isUploading"
                  @click="triggerFileInput"
                >
                  {{ isUploading ? "Läser in fil..." : "Importera från fil" }}
                </button>
              </div>

              <SystemMessage
                v-if="importError"
                :model-value="importError"
                tone="failure"
                dismissible
                role="alert"
                aria-live="assertive"
                aria-atomic="true"
                @update:model-value="updateImportError"
              />

              <div
                v-if="preview"
                class="space-y-2 border border-navy/20 bg-panel-muted p-3"
                data-test="roster-import-summary"
              >
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <div class="space-y-1">
                    <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                      Importförslag
                    </p>
                    <p class="text-sm text-navy">
                      {{ preview.file_name }}
                    </p>
                  </div>
                  <div class="text-right text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                    {{ preview.parsed_students.length }} elever
                  </div>
                </div>
                <p class="text-sm text-navy/70">
                  Klassens namn och elever är ifyllda nedan. Kontrollera att allt stämmer och ändra
                  vid behov.
                </p>
              </div>
            </section>

            <div class="space-y-1">
              <label
                for="roster-name"
                class="text-xs font-semibold uppercase tracking-wide text-navy/70"
              >
                Klassens namn
              </label>
              <input
                id="roster-name"
                v-model="name"
                type="text"
                placeholder="Till exempel Klass 9A"
                class="w-full border border-navy/20 bg-panel px-3 py-2 text-sm text-navy"
              >
            </div>

            <div class="space-y-2">
              <div class="flex items-end justify-between gap-3">
                <label
                  for="roster-students"
                  class="text-xs font-semibold uppercase tracking-wide text-navy/70"
                >
                  Elever
                </label>
                <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                  {{ parsedStudents.length }} namn
                </span>
              </div>
              <textarea
                id="roster-students"
                v-model="rawStudents"
                rows="12"
                placeholder="Anna Andersson&#10;Bilal Berg&#10;Cecilia Ceder"
                class="min-h-[280px] w-full resize-y border border-navy/20 bg-panel px-3 py-3 font-mono text-sm text-navy"
              />
              <p class="text-[11px] leading-relaxed text-navy/60">
                Skriv eller klistra in ett namn per rad.
              </p>
            </div>

            <div
              v-if="ambiguousRows.length > 0"
              class="space-y-3 border border-warning/20 bg-warning/10 p-4"
              data-test="roster-import-ambiguous"
            >
              <div class="space-y-1">
                <p class="text-xs font-semibold uppercase tracking-wide text-warning">
                  Otydliga rader från importen
                </p>
                <p class="text-sm text-warning">
                  Lägg till sådant som faktiskt är elevnamn, eller ignorera rader som inte hör till
                  klasslistan.
                </p>
              </div>

              <div class="space-y-2">
                <div
                  v-for="(row, index) in ambiguousRows"
                  :key="`${row.raw_text}-${index}`"
                  class="space-y-2 border border-warning/20 bg-panel-muted p-3"
                >
                  <div class="break-all font-mono text-sm text-warning">
                    {{ row.raw_text }}
                  </div>
                  <div class="flex flex-wrap gap-3">
                    <button
                      type="button"
                      class="btn-inline-primary"
                      @click="appendAmbiguousRow(index)"
                    >
                      Lägg till i elevlistan
                    </button>
                    <button
                      type="button"
                      class="btn-inline-cancel"
                      @click="dismissAmbiguousRow(index)"
                    >
                      Ignorera
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div
          class="sticky bottom-0 flex flex-col gap-3 border-t border-navy/20 bg-modal px-6 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8"
          data-test="roster-modal-footer"
        >
          <div>
            <button
              v-if="isEditing"
              type="button"
              class="btn-ghost"
              :disabled="isDeleting"
              @click="removeRoster"
            >
              <IconTrash
                v-if="!isDeleting"
                :size="14"
                aria-hidden="true"
              />
              {{ isDeleting ? "Raderar..." : "Radera" }}
            </button>
          </div>
          <div class="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              class="btn-ghost"
              @click="closeModal"
            >
              Avbryt
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="!isValid || isSubmitting"
              @click="submit"
            >
              {{ isSubmitting ? "Sparar..." : isEditing ? "Spara" : "Skapa klasslista" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
