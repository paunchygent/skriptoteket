<script setup lang="ts">
/**
 * Exam Converter report summary.
 *
 * Domain purpose:
 *   Present a compact summary of remaining exam actions and AI suggestion
 *   outcomes so the teacher can return to the relevant question rows.
 *
 * Relationships:
 *   - Rendered only inside the active `Rapport` inspection mode.
 *   - Uses projected action counts and AI suggestion outcome rows.
 *   - Does not expose raw provenance enums or service artifact names.
 */

import type { ExamConverterReportProjection } from "./digiexamIrReviewParser";

defineProps<{
  report: ExamConverterReportProjection;
}>();

const emit = defineEmits<{
  openQuestions: [];
}>();

function aiSuggestionOutcomeLabel(
  outcome: ExamConverterReportProjection["aiSuggestionOutcomes"]["items"][number]["outcome"],
): string {
  if (outcome === "accepted_unchanged") return "Accepterat";
  if (outcome === "teacher_edited") return "Ändrat av lärare";
  if (outcome === "suppressed") return "Avvisat";
  return "Kvar att granska";
}
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
        Rapporten visar kvarvarande åtgärder och hur AI-förslag har hanterats.
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
          AI-förslag
        </h4>
        <dl class="mt-4 grid gap-3 text-sm text-navy">
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Förslag</dt>
            <dd>{{ report.aiSuggestionOutcomes.totalCount.toLocaleString("sv-SE") }}</dd>
          </div>
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Accepterade</dt>
            <dd>
              {{ report.aiSuggestionOutcomes.acceptedUnchangedCount.toLocaleString("sv-SE") }}
            </dd>
          </div>
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Ändrade</dt>
            <dd>{{ report.aiSuggestionOutcomes.teacherEditedCount.toLocaleString("sv-SE") }}</dd>
          </div>
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Avvisade</dt>
            <dd>{{ report.aiSuggestionOutcomes.suppressedCount.toLocaleString("sv-SE") }}</dd>
          </div>
          <div class="grid grid-cols-[12rem_minmax(0,1fr)] gap-3">
            <dt>Kvar att granska</dt>
            <dd>{{ report.aiSuggestionOutcomes.unresolvedCount.toLocaleString("sv-SE") }}</dd>
          </div>
        </dl>

        <p class="mt-4 text-sm leading-snug text-navy/70">
          <template v-if="report.aiSuggestionOutcomes.totalCount === 0">
            Inga AI-förslag hittades för det här provet.
          </template>
          <template v-else-if="report.aiSuggestionOutcomes.unresolvedCount === 0">
            Alla AI-förslag är hanterade.
          </template>
          <template v-else>
            Kontrollera frågorna som fortfarande har AI-förslag.
          </template>
        </p>

        <ol
          v-if="report.aiSuggestionOutcomes.items.length > 0"
          class="mt-4 grid gap-2 text-sm text-navy"
          data-test="exam-converter-report-ai-suggestion-items"
        >
          <li
            v-for="item in report.aiSuggestionOutcomes.items"
            :key="item.itemId"
            class="grid grid-cols-[minmax(0,1fr)_auto] gap-3 border-t border-navy/15 pt-2"
          >
            <span class="min-w-0">
              {{ item.sequence }}. {{ item.title }}
            </span>
            <span class="font-medium">
              {{ aiSuggestionOutcomeLabel(item.outcome) }}
            </span>
          </li>
        </ol>
      </section>

      <div class="flex items-center justify-between gap-4 border border-navy/20 bg-canvas px-4 py-3">
        <p class="text-sm leading-snug text-navy/70">
          När frågor, facit och poäng är klara kan filerna användas.
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
