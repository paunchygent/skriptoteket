<script setup lang="ts">
/**
 * Exam Converter report summary.
 *
 * Domain purpose:
 *   Present a compact diagnostic summary of the converted exam so the teacher
 *   can return to the relevant question rows.
 *
 * Relationships:
 *   - Rendered only inside the active `Rapport` inspection mode.
 *   - Uses the projected migration manifest counts.
 *   - Does not expose raw provenance enums or service artifact names.
 */

import type { ExamConverterReportProjection } from "./digiexamIrReviewParser";

defineProps<{
  report: ExamConverterReportProjection;
}>();

const emit = defineEmits<{
  openQuestions: [];
}>();
</script>

<template>
  <section
    class="py-5"
    data-test="exam-converter-report-summary"
  >
    <div class="flex items-baseline gap-5">
      <h3 class="text-base font-semibold leading-tight text-navy">
        Rapport
      </h3>
      <p class="text-sm leading-tight text-navy/70">
        Rapporten skiljer kvarvarande åtgärder från konverteringsvarningar.
      </p>
    </div>

    <div class="mt-6 grid max-w-[44rem] gap-4">
      <section class="border border-navy/25 bg-panel px-4 py-4">
        <h4 class="text-sm font-semibold leading-tight text-navy">
          Det här behöver kontrolleras
        </h4>
        <dl class="mt-4 grid gap-3 text-sm text-navy">
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Frågor</dt>
            <dd>{{ report.attentionQuestionCount.toLocaleString("sv-SE") }}</dd>
          </div>
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Facit saknas</dt>
            <dd>{{ report.missingAnswerKeyCount.toLocaleString("sv-SE") }}</dd>
          </div>
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Poäng saknas</dt>
            <dd>{{ report.missingPointsCount.toLocaleString("sv-SE") }}</dd>
          </div>
        </dl>
      </section>

      <section class="border border-navy/20 bg-canvas px-4 py-4">
        <h4 class="text-sm font-semibold leading-tight text-navy">
          Konverteringsdiagnostik
        </h4>
        <dl class="mt-4 grid gap-3 text-sm text-navy">
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Konverteringsvarningar</dt>
            <dd>{{ report.warningCount.toLocaleString("sv-SE") }}</dd>
          </div>
        </dl>
      </section>

      <div class="flex items-center justify-between gap-4 border border-navy/20 bg-canvas px-4 py-3">
        <p class="text-sm leading-snug text-navy/70">
          När frågor, facit och poäng är klara kan filerna användas även om
          ursprungliga konverteringsvarningar finns kvar.
        </p>
        <button
          type="button"
          class="btn-ghost shrink-0 justify-center shadow-none"
          data-test="exam-converter-report-open-questions"
          @click="emit('openQuestions')"
        >
          Visa frågor
        </button>
      </div>
    </div>
  </section>
</template>
