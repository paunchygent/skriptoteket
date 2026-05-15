<script setup lang="ts">
/**
 * Exam Converter question review shell.
 *
 * Domain purpose:
 *   Render the read-only question inspection surface from the DigiExam IR
 *   projection with one selected question detail pane.
 *
 * Relationships:
 *   - Rendered only when `Frågor` is the active inspection mode.
 *   - Receives already-projected teacher-facing rows from the IR parser.
 *   - Does not create local completion state or offer edit/export actions.
 */

import { computed, ref, watch } from "vue";
import { AlertTriangle, CheckCircle2 } from "lucide-vue-next";

import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";

const props = defineProps<{
  projection: ExamConverterReviewProjection;
}>();

const selectedItemId = ref<string | null>(null);

const selectedQuestion = computed(() => {
  return (
    props.projection.questions.find((question) => question.itemId === selectedItemId.value) ??
    props.projection.questions[0] ??
    null
  );
});

function defaultSelectedItemId(questions: ExamConverterQuestionReviewRow[]): string | null {
  return (
    questions.find((question) => question.status === "attention")?.itemId ??
    questions[0]?.itemId ??
    null
  );
}

function selectQuestion(question: ExamConverterQuestionReviewRow): void {
  selectedItemId.value = question.itemId;
}

watch(
  () => props.projection.questions,
  (questions) => {
    if (!questions.some((question) => question.itemId === selectedItemId.value)) {
      selectedItemId.value = defaultSelectedItemId(questions);
    }
  },
  { immediate: true },
);
</script>

<template>
  <section
    class="grid min-h-0 flex-1 grid-cols-[minmax(0,1.6fr)_minmax(18rem,0.84fr)] gap-6 py-5"
    data-test="exam-converter-question-review-shell"
  >
    <div class="min-w-0">
      <h3 class="text-base font-semibold leading-tight text-navy">
        Frågor att kontrollera
      </h3>

      <div
        v-if="projection.questions.length === 0"
        class="mt-6 border border-dashed border-navy/35 bg-canvas px-5 py-8 text-sm text-navy/70"
      >
        Inga frågor att visa.
      </div>

      <table
        v-else
        class="mt-6 w-full border-collapse text-left text-sm text-navy"
      >
        <thead>
          <tr class="border-b border-navy/45">
            <th class="px-3 py-3 font-semibold">
              Fråga
            </th>
            <th class="w-32 px-3 py-3 font-semibold">
              Typ
            </th>
            <th class="w-32 px-3 py-3 font-semibold">
              Saknas
            </th>
            <th class="w-24 px-3 py-3 font-semibold">
              Poäng
            </th>
            <th class="w-20 px-3 py-3 text-center font-semibold">
              Status
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="question in projection.questions"
            :key="question.itemId"
            class="cursor-pointer border-b border-navy/15 hover:bg-canvas"
            :class="question.itemId === selectedQuestion?.itemId ? 'bg-navy/5 shadow-[inset_4px_0_0_var(--color-navy)]' : undefined"
            :data-test="`exam-converter-question-row-${question.itemId}`"
            @click="selectQuestion(question)"
          >
            <td class="min-w-0 px-3 py-4 align-top">
              <span class="line-clamp-2">
                <span class="font-semibold">{{ question.sequence }}.</span>
                {{ question.promptText }}
              </span>
            </td>
            <td class="px-3 py-4 align-top">
              {{ question.typeLabel }}
            </td>
            <td class="px-3 py-4 align-top">
              <span
                v-if="question.missingFields.length === 0"
                class="text-navy/70"
              >
                —
              </span>
              <span
                v-for="missingField in question.missingFields"
                v-else
                :key="missingField"
                class="mr-1 inline-flex border border-warning/70 bg-panel px-2 py-1 text-xs font-medium leading-none text-warning"
              >
                {{ missingField }}
              </span>
            </td>
            <td class="px-3 py-4 align-top">
              {{ question.pointsLabel }}
            </td>
            <td class="px-3 py-4 text-center align-top">
              <span
                class="inline-grid h-6 w-6 place-items-center"
                :aria-label="question.status === 'complete' ? 'Klar' : 'Kräver kontroll'"
                role="img"
              >
                <CheckCircle2
                  v-if="question.status === 'complete'"
                  class="h-5 w-5 text-success"
                  aria-hidden="true"
                />
                <AlertTriangle
                  v-else
                  class="h-5 w-5 text-warning"
                  aria-hidden="true"
                />
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <aside
      class="min-w-0 border-l border-navy/35 pl-6"
      data-test="exam-converter-selected-question-detail"
    >
      <template v-if="selectedQuestion">
        <div class="flex items-baseline gap-5">
          <h3 class="text-base font-semibold leading-tight text-navy">
            Fråga {{ selectedQuestion.sequence }}
          </h3>
          <span class="text-sm leading-tight text-navy/60">
            {{ selectedQuestion.itemId }}
          </span>
        </div>

        <p class="mt-5 text-sm leading-relaxed text-navy">
          {{ selectedQuestion.promptText }}
        </p>

        <section class="mt-7">
          <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">
            Finns
          </h4>
          <dl class="mt-4 grid gap-3 text-sm">
            <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
              <dt class="text-navy">
                Typ
              </dt>
              <dd class="text-navy">
                {{ selectedQuestion.typeLabel }}
              </dd>
            </div>
            <div
              v-if="selectedQuestion.pointsLabel !== '—'"
              class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3"
            >
              <dt class="text-navy">
                Poäng
              </dt>
              <dd class="text-navy">
                {{ selectedQuestion.pointsLabel }}
              </dd>
            </div>
          </dl>
        </section>

        <section
          v-if="selectedQuestion.alternatives.length > 0"
          class="mt-7"
          data-test="exam-converter-selected-question-alternatives"
        >
          <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">
            Alternativ
          </h4>
          <ol class="mt-4 grid gap-2 text-sm text-navy">
            <li
              v-for="alternative in selectedQuestion.alternatives"
              :key="alternative.id"
              class="grid grid-cols-[2rem_minmax(0,1fr)] gap-3"
            >
              <span
                class="inline-grid h-7 w-7 place-items-center border border-navy/25 text-xs font-semibold leading-none"
              >
                {{ alternative.id }}
              </span>
              <span class="leading-relaxed">
                {{ alternative.text }}
              </span>
            </li>
          </ol>
        </section>

        <section
          v-if="selectedQuestion.lucktextStructure"
          class="mt-7"
          data-test="exam-converter-selected-question-lucktext"
        >
          <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">
            Lucktext
          </h4>
          <dl class="mt-4 grid gap-3 text-sm">
            <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
              <dt class="text-navy">
                Luckor
              </dt>
              <dd class="text-navy">
                {{ selectedQuestion.lucktextStructure.gapCount }}
              </dd>
            </div>
            <div class="grid grid-cols-[7rem_minmax(0,1fr)] gap-3">
              <dt class="text-navy">
                Bilder
              </dt>
              <dd class="text-navy">
                {{ selectedQuestion.lucktextStructure.imageCount }}
              </dd>
            </div>
          </dl>
          <div
            v-if="selectedQuestion.lucktextStructure.images.length > 0"
            class="mt-4 grid gap-3"
          >
            <figure
              v-for="image in selectedQuestion.lucktextStructure.images"
              :key="image.id"
              class="border border-navy/20 p-3"
            >
              <img
                v-if="image.dataUrl"
                :alt="image.altText"
                class="max-h-56 max-w-full object-contain"
                :src="image.dataUrl"
              >
              <figcaption class="mt-2 text-xs leading-tight text-navy/70">
                {{ image.altText }}
                <span v-if="image.dimensionsLabel">
                  · {{ image.dimensionsLabel }}
                </span>
              </figcaption>
            </figure>
          </div>
        </section>

        <section class="mt-7">
          <h4 class="border-b border-navy/35 pb-2 text-base font-semibold leading-tight text-navy">
            Saknas
          </h4>
          <div class="mt-4">
            <span
              v-if="selectedQuestion.missingFields.length === 0"
              class="text-sm text-navy/70"
            >
              —
            </span>
            <span
              v-for="missingField in selectedQuestion.missingFields"
              v-else
              :key="missingField"
              class="mr-2 inline-flex border border-warning/70 bg-panel px-2 py-1 text-sm font-medium leading-none text-warning"
            >
              {{ missingField }}
            </span>
          </div>
        </section>
      </template>
    </aside>
  </section>
</template>
