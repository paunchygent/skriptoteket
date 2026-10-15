<script setup lang="ts">
/**
 * Export actions in the exam workspace rail.
 *
 * Domain purpose:
 *   Offer QTI, PDF, and DOCX files from the saved version. The server owns
 *   the export gate; this panel only disables the actions for unsaved edits
 *   or work in flight and shows the notice the server outcome produced. After
 *   a QTI export it lists what Exam.net loses on import, so the teacher can
 *   correct those rows in Exam.net.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; emits `export` with the target and the
 *     view runs it through `useExamWorkspaceExports`.
 */

import type {
  ExamWorkspaceExportChecklistEntry,
  ExamWorkspaceExportTarget,
} from "../../../api/examWorkspace";
import { examWorkspaceQuestionLabel } from "./examWorkspaceRows";

const EXPORT_TARGETS: { target: ExamWorkspaceExportTarget; label: string }[] = [
  { label: "QTI", target: "qti" },
  { label: "PDF", target: "pdf" },
  { label: "DOCX", target: "docx" },
];

defineProps<{
  exportChecklist: ExamWorkspaceExportChecklistEntry[];
  exportNotice: string | null;
  exportingTarget: ExamWorkspaceExportTarget | null;
  isBusy: boolean;
  isDirty: boolean;
}>();

const emit = defineEmits<{
  export: [target: ExamWorkspaceExportTarget];
}>();
</script>

<template>
  <section
    class="grid gap-2"
    data-test="exam-workspace-exports"
  >
    <h2 class="text-sm font-semibold leading-tight text-navy">
      Skapa filer
    </h2>
    <div class="grid grid-cols-3 gap-2">
      <button
        v-for="exportOption in EXPORT_TARGETS"
        :key="exportOption.target"
        type="button"
        class="btn-ghost justify-center shadow-none"
        :disabled="isDirty || isBusy || exportingTarget !== null"
        :aria-busy="exportingTarget === exportOption.target ? 'true' : undefined"
        :data-test="`exam-workspace-export-${exportOption.target}`"
        @click="emit('export', exportOption.target)"
      >
        {{ exportOption.label }}
      </button>
    </div>
    <p
      v-if="exportNotice"
      class="text-xs font-semibold leading-snug text-error"
      data-test="exam-workspace-export-notice"
    >
      {{ exportNotice }}
    </p>
    <p
      v-else-if="isDirty"
      class="text-xs leading-snug text-navy/65"
    >
      Spara provet innan du skapar filer. Filerna skapas från den sparade versionen.
    </p>
    <div
      v-if="exportChecklist.length > 0"
      class="grid gap-2 border border-navy/20 bg-canvas px-3 py-2"
    >
      <h3 class="text-xs font-semibold leading-tight text-navy/80">
        Det här tappar Exam.net vid import
      </h3>
      <ul class="grid gap-2">
        <li
          v-for="(entry, index) in exportChecklist"
          :key="index"
          class="grid gap-0.5"
        >
          <p class="text-sm font-medium leading-snug text-navy">
            {{ examWorkspaceQuestionLabel(Number(entry.question_number)) }}:
            {{ entry.question_text }}
          </p>
          <template v-if="entry.kind === 'free_text_criteria'">
            <p
              v-for="(criterion, criterionIndex) in entry.criteria"
              :key="criterionIndex"
              class="text-xs leading-snug text-navy/70"
            >
              {{ criterion.text }} ({{ criterion.points }} p)
            </p>
          </template>
          <p
            v-else-if="entry.kind === 'all_or_nothing'"
            class="text-xs leading-snug text-navy/70"
          >
            Exam.net ger 1 poäng. Sätt {{ entry.points }} poäng.
          </p>
          <p
            v-else
            class="text-xs leading-snug text-navy/70"
          >
            Frågan ger {{ entry.points }} poäng. Varje lucka får {{ entry.gap_points }} poäng.
          </p>
        </li>
      </ul>
    </div>
  </section>
</template>
