<script setup lang="ts">
/**
 * Exam Converter files inspection list.
 *
 * Domain purpose:
 *   Show the teacher which requested files exist after conversion and whether
 *   they should wait for question review before use.
 *
 * Relationships:
 *   - Rendered only inside the active `Filer` inspection mode.
 *   - Receives file rows from the read-only IR/artifact projection.
 *   - Emits download/save intent after the review-decision gate allows export.
 */

import { Download, Save } from "lucide-vue-next";

import type { ExamConverterReviewFile } from "./digiexamIrReviewParser";
import type {
  ExamConverterFileActionState,
  ExamConverterFileActionStates,
} from "./useExamConverterFileActions";

const props = defineProps<{
  actionsEnabled: boolean;
  acceptedCurrentState: boolean;
  actionStates: ExamConverterFileActionStates;
  files: ExamConverterReviewFile[];
}>();

const emit = defineEmits<{
  downloadFile: [file: ExamConverterReviewFile];
  saveFile: [file: ExamConverterReviewFile];
}>();

function actionStateForFile(file: ExamConverterReviewFile): ExamConverterFileActionState {
  return (
    props.actionStates[file.artifactKey] ?? {
      download: "idle",
      save: "idle",
      savedFilename: null,
    }
  );
}

function canUseFile(file: ExamConverterReviewFile): boolean {
  return props.actionsEnabled && file.availability === "available";
}

function statusLabelForFile(file: ExamConverterReviewFile): string {
  const state = actionStateForFile(file);
  if (state.save === "done") {
    return "Sparad i mina filer";
  }
  if (state.download === "done") {
    return "Hämtad";
  }
  if (state.save === "failed") {
    return "Kunde inte sparas";
  }
  if (state.download === "failed") {
    return "Kunde inte hämtas";
  }
  if (file.availability !== "available") {
    return file.statusLabel;
  }
  if (props.actionsEnabled) {
    return props.acceptedCurrentState ? "Godkänt för export" : "Kan hämtas";
  }
  return "Granska eller godkänn först";
}

function downloadLabel(file: ExamConverterReviewFile): string {
  return actionStateForFile(file).download === "running" ? "Hämtar" : "Hämta";
}

function saveLabel(file: ExamConverterReviewFile): string {
  const state = actionStateForFile(file);
  if (state.save === "running") return "Sparar";
  if (state.save === "done") return "Sparad";
  return "Spara";
}

function isDownloadDisabled(file: ExamConverterReviewFile): boolean {
  return !canUseFile(file) || actionStateForFile(file).download === "running";
}

function isSaveDisabled(file: ExamConverterReviewFile): boolean {
  const state = actionStateForFile(file);
  return !canUseFile(file) || state.save === "running" || state.save === "done";
}
</script>

<template>
  <section
    class="py-5"
    data-test="exam-converter-files-readiness-list"
  >
    <div class="flex items-baseline gap-5">
      <h3 class="text-base font-semibold leading-tight text-navy">
        Filer
      </h3>
      <p class="text-sm leading-tight text-navy/70">
        {{ actionsEnabled ? "Filerna kan hämtas eller sparas." : "Granska eller godkänn provet först." }}
      </p>
    </div>

    <div
      v-if="files.length === 0"
      class="mt-6 border border-dashed border-navy/35 bg-canvas px-5 py-8 text-sm text-navy/70"
    >
      Inga filer att visa.
    </div>

    <table
      v-else
      class="mt-6 w-full border-collapse text-left text-sm text-navy"
    >
      <thead>
        <tr class="border-b border-navy/45">
          <th class="px-3 py-3 font-semibold">
            Fil
          </th>
          <th class="w-36 px-3 py-3 font-semibold">
            Format
          </th>
          <th class="w-24 px-3 py-3 font-semibold">
            Storlek
          </th>
          <th class="w-72 px-3 py-3 font-semibold">
            Status
          </th>
          <th class="w-28 px-3 py-3 text-center font-semibold">
            Hämta
          </th>
          <th class="w-36 px-3 py-3 text-center font-semibold">
            Spara
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="file in files"
          :key="file.artifactKey"
          class="border-b border-navy/15"
          :data-test="`exam-converter-file-row-${file.artifactKey}`"
        >
          <td class="px-3 py-4">
            {{ file.filename }}
          </td>
          <td class="px-3 py-4">
            {{ file.kindLabel }}
          </td>
          <td class="px-3 py-4">
            {{ file.sizeLabel ?? "—" }}
          </td>
          <td class="px-3 py-4">
            {{ statusLabelForFile(file) }}
          </td>
          <td class="px-3 py-4 text-center">
            <button
              type="button"
              class="btn-ghost inline-flex items-center justify-center gap-2 shadow-none disabled:cursor-not-allowed disabled:opacity-45"
              :aria-label="`Hämta ${file.filename}`"
              :disabled="isDownloadDisabled(file)"
              :data-test="`exam-converter-download-file-${file.artifactKey}`"
              @click="emit('downloadFile', file)"
            >
              <Download
                class="h-4 w-4 text-action"
                aria-hidden="true"
              />
              {{ downloadLabel(file) }}
            </button>
          </td>
          <td class="px-3 py-4 text-center">
            <button
              type="button"
              class="btn-ghost inline-flex items-center justify-center gap-2 shadow-none disabled:cursor-not-allowed disabled:opacity-45"
              :aria-label="`Spara ${file.filename} i mina filer`"
              :disabled="isSaveDisabled(file)"
              :data-test="`exam-converter-save-file-${file.artifactKey}`"
              @click="emit('saveFile', file)"
            >
              <Save
                class="h-4 w-4 text-action"
                aria-hidden="true"
              />
              {{ saveLabel(file) }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
