<script setup lang="ts">
/**
 * Exam Converter review decision gate.
 *
 * Domain purpose:
 *   Let the teacher either review missing question data or accept the current
 *   conversion state before file export/save actions become available.
 *
 * Relationships:
 *   - Rendered after the result strip when questions need a teacher decision.
 *   - Emits navigation/acceptance intent only; it does not mutate Sir Convert IR.
 */

import { Check, ListChecks } from "lucide-vue-next";

defineProps<{
  accepted: boolean;
  blockedFileCount: number;
  missingCount: number;
}>();

const emit = defineEmits<{
  acceptCurrentState: [];
  reviewQuestions: [];
}>();

const reviewHelp = "Granska och redigera frågorna som saknar facit eller poäng.";
const acceptHelp = "Hoppa över granskningen och exportera provet direkt.";
</script>

<template>
  <section
    class="mt-3 grid gap-3 border border-navy/35 bg-panel px-3 py-2 md:grid-cols-[minmax(0,1fr)_auto] md:items-center"
    data-test="exam-converter-review-decision-gate"
  >
    <p class="min-w-0 text-sm font-medium leading-tight text-navy">
      <span v-if="accepted">
        Godkänt som det är
      </span>
      <span v-else>
        <template v-if="missingCount > 0">
          {{ missingCount.toLocaleString("sv-SE") }}
          {{ missingCount === 1 ? "fråga" : "frågor" }} saknar facit eller poäng.
        </template>
        <template v-else>
          {{ blockedFileCount.toLocaleString("sv-SE") }}
          {{ blockedFileCount === 1 ? "målfil behöver" : "målfiler behöver" }}
          godkännas för export.
        </template>
      </span>
    </p>

    <div
      v-if="!accepted"
      class="grid w-full grid-cols-[minmax(6.5rem,1fr)_minmax(6.5rem,1fr)] items-center gap-2 md:w-auto md:grid-cols-[minmax(6.5rem,auto)_minmax(6.5rem,auto)]"
      aria-label="Välj hur provet ska fortsätta"
    >
      <button
        v-if="missingCount > 0"
        type="button"
        class="btn-ghost inline-flex items-center gap-2 shadow-none"
        :title="reviewHelp"
        data-test="exam-converter-review-questions-action"
        @click="emit('reviewQuestions')"
      >
        <ListChecks
          class="h-4 w-4 text-action"
          aria-hidden="true"
        />
        Granska
      </button>
      <span
        v-else
        class="btn-ghost invisible inline-flex items-center gap-2 shadow-none"
        aria-hidden="true"
        data-test="exam-converter-review-questions-placeholder"
      >
        <ListChecks
          class="h-4 w-4 text-action"
          aria-hidden="true"
        />
        Granska
      </span>
      <button
        type="button"
        class="btn-primary inline-flex items-center gap-2 shadow-none"
        :title="acceptHelp"
        data-test="exam-converter-accept-current-state-action"
        @click="emit('acceptCurrentState')"
      >
        <Check
          class="h-4 w-4"
          aria-hidden="true"
        />
        Godkänn
      </button>
    </div>
  </section>
</template>
