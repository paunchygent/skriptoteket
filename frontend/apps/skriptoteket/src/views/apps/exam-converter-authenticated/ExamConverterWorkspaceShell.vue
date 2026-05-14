<script setup lang="ts">
/**
 * Exam Converter workspace shell.
 *
 * Domain purpose:
 *   Reserve the dominant right-side workspace for approved Exam Converter
 *   intake, result, inspection, and review slices while keeping the host frame
 *   free of transport or conversion behavior.
 *
 * Relationships:
 *   - Rendered by `ExamConverterAuthenticatedView`.
 *   - Owns the idle source-file drop zone before later slices replace it with
 *     result strip, inspection modes, and focused review surfaces.
 */

import { FileText, Upload } from "lucide-vue-next";

import type { ExamConverterSourceFileSelection } from "./useExamConverterSourceFile";

defineProps<{
  selectedSourceFile: ExamConverterSourceFileSelection | null;
  sourceFileError: string | null;
}>();

const emit = defineEmits<{
  sourceFileSelected: [file: File];
}>();

function selectFirstFile(fileList: FileList | null): void {
  const [file] = Array.from(fileList ?? []);
  if (file) {
    emit("sourceFileSelected", file);
  }
}

function handleFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  selectFirstFile(input.files);
  input.value = "";
}

function handleDrop(event: DragEvent): void {
  event.preventDefault();
  selectFirstFile(event.dataTransfer?.files ?? null);
}
</script>

<template>
  <section
    class="flex h-full min-h-[26rem] flex-col bg-panel"
    aria-labelledby="exam-converter-auth-title"
    data-test="exam-converter-workspace-shell"
  >
    <header class="px-4 py-4">
      <div class="min-w-0">
        <h2
          id="exam-converter-auth-title"
          class="text-lg font-semibold leading-tight text-navy"
        >
          {{ selectedSourceFile ? "Provfilen är vald" : "Välj provfil för att börja" }}
        </h2>
        <p class="mt-1 text-sm leading-snug text-navy/70">
          {{ selectedSourceFile ? "Nästa steg är att starta konverteringen." : "Dra hit .dxe-filen eller välj fil från datorn." }}
        </p>
      </div>
    </header>

    <div class="flex min-h-0 flex-1 px-4 pb-4">
      <label
        class="grid min-h-0 w-full flex-1 border border-dashed border-navy/45 bg-canvas px-6 py-6"
        :class="sourceFileError ? 'border-error bg-error/5' : undefined"
        data-test="exam-converter-source-drop-zone"
        @dragover.prevent
        @drop="handleDrop"
      >
        <input
          class="sr-only"
          type="file"
          accept=".dxe"
          data-test="exam-converter-source-file-input"
          @change="handleFileInput"
        >
        <div class="flex h-full min-w-0 items-center justify-center gap-4">
          <span
            class="grid h-12 w-12 shrink-0 place-items-center border border-navy/25 bg-panel"
            aria-hidden="true"
          >
            <FileText
              v-if="selectedSourceFile"
              class="h-6 w-6 text-navy"
            />
            <Upload
              v-else
              class="h-6 w-6 text-action"
            />
          </span>
          <div class="min-w-0">
            <p class="text-base font-medium leading-tight text-navy">
              {{ selectedSourceFile?.name ?? "Välj provfil" }}
            </p>
            <p
              v-if="selectedSourceFile"
              class="mt-2 text-sm leading-snug text-navy/70"
            >
              {{ selectedSourceFile.sizeLabel }}
            </p>
            <p
              v-else-if="sourceFileError"
              class="mt-2 text-sm leading-snug text-error"
            >
              {{ sourceFileError }}
            </p>
          </div>
        </div>
      </label>
    </div>
  </section>
</template>
