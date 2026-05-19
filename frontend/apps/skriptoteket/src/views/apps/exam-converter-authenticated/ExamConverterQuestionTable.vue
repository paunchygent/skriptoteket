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

import { Bot, CheckCircle2, XCircle } from "lucide-vue-next";

import type { ExamConverterQuestionReviewRow } from "./digiexamIrReviewParser";
import { visibleMissingFieldsForQuestion } from "./digiexamIrReviewParser";

defineProps<{
  questions: ExamConverterQuestionReviewRow[];
  selectedItemId: string | null;
}>();

const emit = defineEmits<{
  questionSelected: [question: ExamConverterQuestionReviewRow];
}>();

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
        <th class="w-24 px-2 py-3 font-semibold xl:w-28">
          Saknas
        </th>
        <th class="w-20 px-2 py-3 font-semibold">
          Poäng
        </th>
        <th class="w-16 px-2 py-3 text-center font-semibold">
          Status
        </th>
      </tr>
    </thead>
    <tbody>
      <tr
        v-for="question in questions"
        :key="question.itemId"
        class="cursor-pointer border-b border-navy/15"
        :class="question.itemId === selectedItemId ? 'bg-navy/5 shadow-[inset_4px_0_0_var(--color-navy)]' : 'hover:bg-canvas'"
        :data-test="`exam-converter-question-row-${question.itemId}`"
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
          <span
            v-if="visibleMissingFieldsForQuestion(question).length === 0"
            class="text-navy/70"
          >
            —
          </span>
          <span
            v-for="missingField in visibleMissingFieldsForQuestion(question)"
            v-else
            :key="missingField"
            class="mr-1 inline-flex border border-warning/70 bg-panel px-2 py-1 text-xs font-medium leading-none text-warning"
          >
            {{ missingField }}
          </span>
        </td>
        <td class="px-2 py-4 align-top">
          {{ question.pointsLabel }}
        </td>
        <td class="px-2 py-4 text-center align-top">
          <span
            class="inline-grid h-6 w-6 place-items-center"
            :aria-label="question.statusSymbol === 'ai_suggestion' ? 'AI-förslag' : question.statusSymbol === 'complete' ? 'Klar' : 'Saknar facit'"
            role="img"
          >
            <Bot
              v-if="question.statusSymbol === 'ai_suggestion'"
              class="h-5 w-5 text-success"
              aria-hidden="true"
            />
            <CheckCircle2
              v-else-if="question.statusSymbol === 'complete'"
              class="h-5 w-5 text-success"
              aria-hidden="true"
            />
            <XCircle
              v-else
              class="h-5 w-5 text-error"
              aria-hidden="true"
            />
          </span>
        </td>
      </tr>
    </tbody>
  </table>
</template>
