<script setup lang="ts">
/**
 * Exam Converter workflow rail shell.
 *
 * Domain purpose:
 *   Reserve the stable left-side Exam Converter setup rail for source-file
 *   state, optional supporting file state, target-file declarations, and later
 *   conversion actions without becoming the primary work surface.
 *
 * Relationships:
 *   - Rendered by `ExamConverterAuthenticatedView`.
 *   - Receives browser-local source-file state from the authenticated host.
 */

import { Check, FileText, HelpCircle, Play, Upload, X } from "lucide-vue-next";

import type {
  ExamConverterSourceFileSelection,
  ExamConverterTargetFormat,
  ExamConverterTargetSelection,
} from "./useExamConverterSourceFile";

defineProps<{
  canStartConversion: boolean;
  isConversionRunning: boolean;
  selectedSupportingFile: ExamConverterSourceFileSelection | null;
  selectedSourceFile: ExamConverterSourceFileSelection | null;
  selectedTargetFormats: ExamConverterTargetSelection;
  supportingFileError: string | null;
}>();

const emit = defineEmits<{
  clearSupportingFile: [];
  clearSourceFile: [];
  resetLocalChoices: [];
  startConversion: [];
  sourceFileSelected: [file: File];
  supportingFileSelected: [file: File];
  toggleTargetFormat: [format: ExamConverterTargetFormat];
}>();

function firstFile(fileList: FileList | null): File | null {
  const [file] = Array.from(fileList ?? []);
  return file ?? null;
}

function handleSourceFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = firstFile(input.files);
  if (file) {
    emit("sourceFileSelected", file);
  }
  input.value = "";
}

function handleSupportingFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = firstFile(input.files);
  if (file) {
    emit("supportingFileSelected", file);
  }
  input.value = "";
}
</script>

<template>
  <aside
    class="exam-converter-workflow-rail-shell border-b border-navy/20 bg-panel p-4 xl:border-b-0 xl:border-r"
    aria-labelledby="exam-converter-workflow-title"
    data-test="exam-converter-workflow-rail-shell"
  >
    <div>
      <h1
        id="exam-converter-workflow-title"
        class="text-base font-semibold leading-tight text-navy"
      >
        Konvertera prov
      </h1>
    </div>

    <div class="exam-converter-workflow-rail-body mt-5 grid gap-6">
      <section
        class="grid gap-2"
        data-test="exam-converter-source-file-state"
      >
        <h2 class="text-sm font-semibold leading-tight text-navy">
          1. Provfil
        </h2>
        <div
          v-if="selectedSourceFile"
          class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border border-navy/25 bg-panel px-3 py-3"
          data-test="exam-converter-selected-source-file"
        >
          <FileText
            class="h-5 w-5 text-navy"
            aria-hidden="true"
          />
          <span class="min-w-0">
            <span class="block truncate text-sm font-medium leading-snug text-navy">
              {{ selectedSourceFile.name }}
            </span>
            <span class="mt-0.5 block text-xs leading-none text-navy/65">
              {{ selectedSourceFile.sizeLabel }}
            </span>
          </span>
          <button
            type="button"
            class="grid h-7 w-7 place-items-center border border-navy/25 bg-panel-muted text-navy hover:bg-canvas focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action"
            aria-label="Ta bort provfil"
            data-test="exam-converter-clear-source-file"
            :disabled="isConversionRunning"
            @click="emit('clearSourceFile')"
          >
            <X
              class="h-4 w-4"
              aria-hidden="true"
            />
          </button>
        </div>
        <label
          v-else
          class="grid cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border border-navy/25 bg-panel px-3 py-3 hover:bg-canvas"
          :class="isConversionRunning ? 'cursor-not-allowed opacity-60' : undefined"
          data-test="exam-converter-source-file-action"
        >
          <input
            class="sr-only"
            type="file"
            accept=".dxe"
            data-test="exam-converter-rail-source-file-input"
            :disabled="isConversionRunning"
            @change="handleSourceFileInput"
          >
          <Upload
            class="h-5 w-5 text-action"
            aria-hidden="true"
          />
          <span class="min-w-0 text-sm font-medium leading-snug text-navy">
            Välj provfil (.dxe)
          </span>
        </label>
        <p
          v-if="!selectedSourceFile"
          class="exam-converter-workflow-rail-secondary text-xs leading-snug text-navy/65"
        >
          Ingen fil vald.
        </p>
        <p
          v-else
          class="flex items-center gap-2 text-xs leading-snug text-success"
        >
          <Check
            class="h-3 w-3"
            aria-hidden="true"
          />
          Filen är uppladdad
        </p>
      </section>

      <section
        class="grid gap-2"
        data-test="exam-converter-supporting-file-state"
      >
        <h2 class="text-sm font-semibold leading-tight text-navy">
          2. Valfritt rättat prov
        </h2>
        <div
          v-if="selectedSupportingFile"
          class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border border-navy/25 bg-panel px-3 py-3"
          data-test="exam-converter-selected-supporting-file"
        >
          <FileText
            class="h-5 w-5 text-navy"
            aria-hidden="true"
          />
          <span class="min-w-0">
            <span class="block truncate text-sm font-medium leading-snug text-navy">
              {{ selectedSupportingFile.name }}
            </span>
            <span class="mt-0.5 block text-xs leading-none text-navy/65">
              {{ selectedSupportingFile.sizeLabel }}
            </span>
          </span>
          <button
            type="button"
            class="grid h-7 w-7 place-items-center border border-navy/25 bg-panel-muted text-navy hover:bg-canvas"
            aria-label="Ta bort resultat-PDF"
            data-test="exam-converter-clear-supporting-file"
            :disabled="isConversionRunning"
            @click="emit('clearSupportingFile')"
          >
            <X
              class="h-4 w-4"
              aria-hidden="true"
            />
          </button>
        </div>
        <label
          v-else
          class="grid cursor-pointer grid-cols-[auto_minmax(0,1fr)] items-center gap-3 border border-navy/25 bg-panel px-3 py-3 hover:bg-canvas"
          :class="[
            supportingFileError ? 'border-error bg-error/5' : undefined,
            isConversionRunning ? 'cursor-not-allowed opacity-60' : undefined,
          ]"
          data-test="exam-converter-supporting-file-action"
        >
          <input
            class="sr-only"
            type="file"
            accept=".pdf"
            data-test="exam-converter-supporting-file-input"
            :disabled="isConversionRunning"
            @change="handleSupportingFileInput"
          >
          <FileText
            class="h-5 w-5 text-navy"
            aria-hidden="true"
          />
          <span class="min-w-0 text-sm font-medium leading-snug text-navy">
            Välj fil (.pdf)
          </span>
        </label>
        <p
          v-if="supportingFileError"
          class="text-xs leading-snug text-error"
        >
          {{ supportingFileError }}
        </p>
        <p
          v-else-if="selectedSupportingFile"
          class="flex items-center gap-2 text-xs leading-snug text-success"
        >
          <Check
            class="h-3 w-3"
            aria-hidden="true"
          />
          Filen är uppladdad
        </p>
        <p
          v-else
          class="exam-converter-workflow-rail-secondary text-xs leading-snug text-navy/65"
        >
          Ingen fil vald.
        </p>
        <p class="exam-converter-workflow-rail-secondary text-xs leading-snug text-navy/65">
          Kan dras in samtidigt med provfilen.
        </p>
      </section>

      <section
        class="grid gap-2"
        data-test="exam-converter-target-file-state"
      >
        <h2 class="text-sm font-semibold leading-tight text-navy">
          3. Målfiler
        </h2>
        <div class="grid gap-2">
          <button
            type="button"
            class="border px-3 py-3 text-left disabled:cursor-not-allowed disabled:opacity-50"
            :class="[
              selectedTargetFormats.pdf ? 'border-navy/25 bg-panel' : 'border-navy/20 bg-panel-muted opacity-75',
              'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action',
            ]"
            :aria-pressed="selectedTargetFormats.pdf"
            data-test="exam-converter-target-pdf"
            :disabled="isConversionRunning"
            @click="emit('toggleTargetFormat', 'pdf')"
          >
            <div class="flex items-center gap-2 text-sm font-medium leading-snug text-navy">
              <span
                class="grid h-5 w-5 place-items-center border border-navy"
                :class="selectedTargetFormats.pdf ? 'bg-navy text-button-primary-text' : 'bg-panel text-navy'"
              >
                <Check
                  v-if="selectedTargetFormats.pdf"
                  class="h-3 w-3"
                  aria-hidden="true"
                />
              </span>
              PDF
              <HelpCircle
                class="ml-auto h-4 w-4 text-action"
                aria-hidden="true"
              />
            </div>
            <p class="exam-converter-workflow-rail-secondary mt-2 text-xs leading-snug text-navy/65">
              För direktimport av prov i Exam.net.
            </p>
          </button>

          <button
            type="button"
            class="border px-3 py-3 text-left disabled:cursor-not-allowed disabled:opacity-50"
            :class="[
              selectedTargetFormats.qti ? 'border-navy/25 bg-panel' : 'border-navy/20 bg-panel-muted opacity-75',
              'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action',
            ]"
            :aria-pressed="selectedTargetFormats.qti"
            data-test="exam-converter-target-qti"
            :disabled="isConversionRunning"
            @click="emit('toggleTargetFormat', 'qti')"
          >
            <div class="flex items-center gap-2 text-sm font-medium leading-snug text-navy">
              <span
                class="grid h-5 w-5 place-items-center border border-navy"
                :class="selectedTargetFormats.qti ? 'bg-navy text-button-primary-text' : 'bg-panel text-navy'"
              >
                <Check
                  v-if="selectedTargetFormats.qti"
                  class="h-3 w-3"
                  aria-hidden="true"
                />
              </span>
              QTI-format
              <HelpCircle
                class="ml-auto h-4 w-4 text-action"
                aria-hidden="true"
              />
            </div>
            <p class="exam-converter-workflow-rail-secondary mt-2 text-xs leading-snug text-navy/65">
              För lagring och import av digitala prov.
            </p>
          </button>
        </div>
      </section>

      <section class="exam-converter-workflow-rail-actions grid gap-3">
        <h2 class="text-sm font-semibold leading-tight text-navy">
          4. Konvertera
        </h2>
        <div class="exam-converter-workflow-actions-grid grid gap-3">
          <button
            type="button"
            class="btn-cta justify-center gap-2 shadow-none"
            :disabled="!canStartConversion || isConversionRunning"
            data-test="exam-converter-start-conversion"
            @click="emit('startConversion')"
          >
            <Play
              class="h-4 w-4"
              aria-hidden="true"
            />
            <span class="exam-converter-action-label-full">Starta konvertering</span>
            <span class="exam-converter-action-label-compact">Starta</span>
          </button>
          <button
            type="button"
            class="btn-ghost justify-center shadow-none"
            data-test="exam-converter-reset-local-choices"
            @click="emit('resetLocalChoices')"
          >
            <span class="exam-converter-action-label-full">Rensa val</span>
            <span class="exam-converter-action-label-compact">Rensa</span>
          </button>
        </div>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.exam-converter-action-label-compact {
  display: none;
}

@media (min-width: 1024px) and (max-width: 1279px) {
  .exam-converter-workflow-rail-shell {
    padding-block: 0.875rem;
  }

  .exam-converter-workflow-rail-body {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
    margin-top: 0.75rem;
  }

  .exam-converter-workflow-rail-secondary {
    display: none;
  }

  .exam-converter-workflow-rail-body :deep([data-test="exam-converter-target-file-state"] > div) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .exam-converter-workflow-rail-body :deep([data-test="exam-converter-target-pdf"]),
  .exam-converter-workflow-rail-body :deep([data-test="exam-converter-target-qti"]) {
    min-height: 2.625rem;
    padding-inline: 0.625rem;
  }

  .exam-converter-workflow-actions-grid {
    grid-template-columns: minmax(0, 1.35fr) minmax(0, 0.9fr);
    gap: 0.5rem;
  }

  .exam-converter-action-label-full {
    display: none;
  }

  .exam-converter-action-label-compact {
    display: inline;
  }

  .exam-converter-workflow-rail-actions :deep(.btn-cta),
  .exam-converter-workflow-rail-actions :deep(.btn-ghost) {
    min-height: 2.625rem;
    padding-inline: 0.625rem;
  }

  .exam-converter-workflow-rail-body :deep(section) {
    align-content: start;
    gap: 0.5rem;
  }

  .exam-converter-workflow-rail-body :deep(button),
  .exam-converter-workflow-rail-body :deep(label),
  .exam-converter-workflow-rail-body :deep([data-test="exam-converter-selected-source-file"]),
  .exam-converter-workflow-rail-body :deep([data-test="exam-converter-selected-supporting-file"]) {
    padding-block: 0.625rem;
  }
}
</style>
