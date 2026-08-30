<script setup lang="ts">
/**
 * Exam Converter question table.
 *
 * Domain purpose:
 *   Render the desktop review table for imported question rows while preserving
 *   row selection behavior for the selected-question inspector.
 *
 * Relationships:
 *   - Rendered by `ExamConverterQuestionReviewShell` at desktop widths.
 *   - Shares review row contracts with `ExamConverterQuestionNavigator`.
 */

import {
  IconAi,
  IconCheck,
  IconEdit,
  IconNextPage,
  IconWarning,
} from "../../../components/icons";

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";

defineProps<{
  questions: ExamConverterQuestionReviewRow[];
  selectedItemId: string | null;
}>();

const emit = defineEmits<{
  questionSelected: [question: ExamConverterQuestionReviewRow];
}>();

function statusSymbolLabel(question: ExamConverterQuestionReviewRow): string {
  if (question.statusSymbol === "ai_suggestion") return "Förslag";
  if (question.statusSymbol === "validation_required") return "Saknar facit";
  return question.answerKeyReviewStateLabel;
}
</script>

<template>
  <table class="w-full table-fixed border-collapse text-left text-sm text-navy">
    <thead>
      <tr class="border-b border-navy/45">
        <th class="px-3 py-3 font-semibold">
          Fråga
        </th>
        <th class="w-24 px-2 py-3 font-semibold xl:w-28">
          Typ
        </th>
        <th class="w-20 px-2 py-3 font-semibold">
          Poäng
        </th>
        <th class="w-36 px-2 py-3 text-left font-semibold">
          Status
        </th>
        <th class="w-14 px-2 py-3">
          <span class="sr-only">Öppna</span>
        </th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="question in questions"
        :key="question.itemId"
        :aria-selected="question.itemId === selectedItemId ? 'true' : 'false'"
        class="cursor-pointer border-b border-navy/15"
        :class="question.itemId === selectedItemId ? 'bg-navy/5 shadow-[inset_4px_0_0_var(--color-navy)]' : 'hover:bg-canvas'"
        :data-test="`exam-converter-question-row-${question.itemId}`"
        role="row"
        @click="emit('questionSelected', question)"
      >
        <td class="min-w-0 px-3 py-4 align-top">
          <span class="line-clamp-2">
            <span class="font-semibold">{{ question.sequence }}.</span>
            {{ question.promptText }}
          </span>
        </td>
        <td class="px-2 py-4 align-top">
          {{ question.typeLabel }}
        </td>
        <td class="px-2 py-4 align-top">
          {{ question.pointsLabel }}
        </td>
        <td class="px-2 py-4 text-left align-middle">
          <span
            class="inline-flex items-center gap-2"
            :aria-label="statusSymbolLabel(question)"
            role="img"
          >
            <IconAi
              v-if="question.statusSymbol === 'ai_suggestion'"
              :size="20"
              class="h-5 w-5 shrink-0 text-navy"
              aria-hidden="true"
            />
            <IconCheck
              v-else-if="question.statusSymbol === 'complete'"
              :size="20"
              class="h-5 w-5 text-success"
              aria-hidden="true"
            />
            <IconEdit
              v-else-if="question.statusSymbol === 'teacher_modified'"
              :size="20"
              class="h-5 w-5 text-navy"
              aria-hidden="true"
            />
            <IconWarning
              v-else
              :size="20"
              class="h-5 w-5 shrink-0 text-warning"
              aria-hidden="true"
            />
            <span class="text-xs font-semibold leading-tight text-navy">
              {{ statusSymbolLabel(question) }}
            </span>
          </span>
        </td>
        <td class="px-2 py-4 text-right align-middle">
          <button
            type="button"
            class="btn-ghost grid h-10 w-10 place-items-center p-0 shadow-none"
            :aria-label="`Öppna fråga ${question.sequence}`"
            @click.stop="emit('questionSelected', question)"
          >
            <IconNextPage
              :size="18"
              class="h-[1.125rem] w-[1.125rem] text-navy/65"
            />
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</template>
