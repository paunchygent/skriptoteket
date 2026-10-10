<script setup lang="ts">
/**
 * Export actions in the exam workspace rail.
 *
 * Domain purpose:
 *   Offer QTI, PDF, and DOCX files from the saved version. The server owns
 *   the export gate; this panel only disables the actions for unsaved edits
 *   or work in flight and shows the notice the server outcome produced.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView`; emits `export` with the target and the
 *     view runs it through `useExamWorkspaceExports`.
 */

import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspace";

const EXPORT_TARGETS: { target: ExamWorkspaceExportTarget; label: string }[] = [
  { label: "QTI", target: "qti" },
  { label: "PDF", target: "pdf" },
  { label: "DOCX", target: "docx" },
];

defineProps<{
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
  </section>
</template>
