<script setup lang="ts">
/**
 * Exam Converter upload panel.
 *
 * Domain purpose:
 *   Present teacher input controls for `.dxe`, optional result-PDF, target
 *   selection, and submit without owning runtime state or backend calls.
 *
 * Relationships:
 *   - Emits file and target changes to public or authenticated runtime
 *     composables.
 *   - Uses shared dense UI primitives for tokenized button behavior.
 */

import { FileArchive, FileText, Upload } from "lucide-vue-next";

import UiDenseActionButton from "../../../components/ui/UiDenseActionButton.vue";
import type { ExamConverterTarget } from "./types";

const props = defineProps<{
  sourceDxeFileName: string | null;
  gradedResultPdfFileName: string | null;
  selectedTargets: ExamConverterTarget[];
  canSubmit: boolean;
  isSubmitting: boolean;
}>();

const emit = defineEmits<{
  sourceFileChange: [file: File | null];
  gradedResultFileChange: [file: File | null];
  targetChange: [target: ExamConverterTarget, checked: boolean];
  submit: [];
}>();

function firstSelectedFile(event: Event): File | null {
  const input = event.target as HTMLInputElement;
  return input.files?.[0] ?? null;
}

function onSourceChange(event: Event): void {
  emit("sourceFileChange", firstSelectedFile(event));
}

function onGradedResultChange(event: Event): void {
  emit("gradedResultFileChange", firstSelectedFile(event));
}

function onTargetChange(target: ExamConverterTarget, event: Event): void {
  emit("targetChange", target, (event.target as HTMLInputElement).checked);
}
</script>

<template>
  <form
    class="border border-navy bg-panel p-4 shadow-brutal-sm"
    @submit.prevent="emit('submit')"
  >
    <label
      class="mb-3 flex min-h-[72px] cursor-pointer items-center gap-3 border border-navy/25 bg-canvas/55 p-3 text-navy transition-colors hover:bg-canvas"
    >
      <span class="grid h-11 w-11 shrink-0 place-items-center border border-navy/20 bg-panel-muted">
        <Upload
          class="h-[18px] w-[18px]"
          aria-hidden="true"
        />
      </span>
      <span class="min-w-0">
        <span class="block text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          DigiExam .dxe
        </span>
        <strong class="block break-words text-sm">
          {{ props.sourceDxeFileName ?? "Välj fil" }}
        </strong>
      </span>
      <input
        class="sr-only"
        accept=".dxe"
        type="file"
        @change="onSourceChange"
      >
    </label>

    <label
      class="mb-4 flex min-h-[72px] cursor-pointer items-center gap-3 border border-navy/25 bg-canvas/55 p-3 text-navy transition-colors hover:bg-canvas"
    >
      <span class="grid h-11 w-11 shrink-0 place-items-center border border-navy/20 bg-panel-muted">
        <FileText
          class="h-[18px] w-[18px]"
          aria-hidden="true"
        />
      </span>
      <span class="min-w-0">
        <span class="block text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Resultat-PDF
        </span>
        <strong class="block break-words text-sm">
          {{ props.gradedResultPdfFileName ?? "Valfri fil" }}
        </strong>
      </span>
      <input
        class="sr-only"
        accept="application/pdf,.pdf"
        type="file"
        @change="onGradedResultChange"
      >
    </label>

    <fieldset class="mb-4 grid gap-2 border-0 p-0">
      <legend class="mb-2 text-sm font-semibold text-navy">Målformat</legend>
      <label class="flex items-center gap-2 text-sm font-semibold text-navy">
        <input
          :checked="props.selectedTargets.includes('examnet_pdf')"
          type="checkbox"
          @change="onTargetChange('examnet_pdf', $event)"
        >
        <span class="flex items-center gap-2">
          <FileText
            class="h-[18px] w-[18px]"
            aria-hidden="true"
          />
          Exam.net PDF
        </span>
      </label>
      <label class="flex items-center gap-2 text-sm font-semibold text-navy">
        <input
          :checked="props.selectedTargets.includes('qti_package')"
          type="checkbox"
          @change="onTargetChange('qti_package', $event)"
        >
        <span class="flex items-center gap-2">
          <FileArchive
            class="h-[18px] w-[18px]"
            aria-hidden="true"
          />
          QTI-paket
        </span>
      </label>
    </fieldset>

    <UiDenseActionButton
      class="h-10 w-full text-sm"
      label="Konvertera"
      tone="primary"
      type="submit"
      :busy="props.isSubmitting"
      busy-label="Konverterar"
      :disabled="!props.canSubmit"
    >
      <template #leading>
        <Upload class="h-[18px] w-[18px]" />
      </template>
    </UiDenseActionButton>
  </form>
</template>
