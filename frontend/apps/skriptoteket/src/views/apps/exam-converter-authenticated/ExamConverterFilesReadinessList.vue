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
  actionNotice: string | null;
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
  return props.actionsEnabled && file.exportEnabled && file.artifactActionReference !== null;
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
  if (canUseFile(file)) {
    return "Kan hämtas";
  }
  if (file.exportEnabled && !file.artifactActionReference) {
    return "Filer kunde inte skapas";
  }
  return file.statusLabel;
}

function reasonLabelForFile(file: ExamConverterReviewFile): string | null {
  if (file.exportEnabled && !file.artifactActionReference) {
    return "Filen kunde inte hämtas efter senaste sparningen.";
  }
  if (file.exportEnabled || !file.reasonCode) {
    return null;
  }
  switch (file.reasonCode) {
    case "manual_answer_key_required":
      return "Facit eller poäng saknas.";
    case "manual_marking_required":
      return "Filen väntar på att skapas.";
    case "unsupported_target_shape":
      return "Målfilen kunde inte skapas. Granska rapporten.";
    case "target_validation_failed":
      return "Målfilen kunde inte skapas i ett importklart format.";
    case "qti_package_export_disabled":
      return "QTI-filen kunde inte skapas. Granska rapporten.";
    case "provider_unavailable":
      return "Facitförslag kunde inte tas fram just nu.";
    case "not_requested":
      return "Formatet valdes inte för den här konverteringen.";
    case "not_implemented":
      return "Formatet kan inte skapas i den här konverteringen.";
    case "target_available":
      return null;
    default:
      return "Målfilen kunde inte skapas. Granska rapporten.";
  }
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
    </div>
    <p
      v-if="actionNotice"
      class="mt-3 border border-navy/15 bg-canvas px-3 py-2 text-sm leading-snug text-navy/75"
      data-test="exam-converter-file-action-notice"
    >
      {{ actionNotice }}
    </p>

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
            <span class="block">
              {{ statusLabelForFile(file) }}
            </span>
            <span
              v-if="reasonLabelForFile(file)"
              class="mt-1 block text-xs leading-snug text-navy/65"
              :data-test="`exam-converter-file-reason-${file.artifactKey}`"
            >
              {{ reasonLabelForFile(file) }}
            </span>
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
