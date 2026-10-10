<script setup lang="ts">
/**
 * Advisory answer-key proposal for the selected exam workspace item.
 *
 * Domain purpose:
 *   Show the machine-proposed answer key next to the item editor and let the
 *   teacher approve it unchanged, move it into the editor to adjust, or
 *   dismiss it. Nothing is applied until the teacher acts.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` for the selected item's open proposal.
 *   - Emits intents; `useExamWorkspaceDocument` applies them to local state.
 */

import { computed } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";

const props = defineProps<{
  disabled: boolean;
  item: NativeExamItem;
  proposedItem: NativeExamItem;
}>();

const emit = defineEmits<{
  approve: [itemId: string];
  dismiss: [itemId: string];
  edit: [itemId: string];
}>();

const proposedChoiceTexts = computed(() =>
  props.item.choices
    .filter((choice) => props.proposedItem.answer_key.correct_choice_ids.includes(choice.choice_id))
    .map((choice) => choice.text),
);

const proposedGapValues = computed(() =>
  props.proposedItem.gaps.map((gap, index) => ({
    gapId: gap.gap_id,
    label: `Lucka ${index + 1}`,
    values: gap.accepted_values.join(", "),
  })),
);
</script>

<template>
  <section
    class="grid gap-3 border border-navy bg-panel p-3"
    :aria-label="`Facitförslag för fråga ${item.sequence}`"
    data-test="exam-workspace-proposal-panel"
  >
    <header class="grid gap-1">
      <h3 class="text-sm font-semibold leading-tight text-navy">
        Facitförslag
      </h3>
      <p class="text-xs leading-snug text-navy/65">
        Förslaget är framtaget av AI. Kontrollera det innan du godkänner.
      </p>
    </header>

    <ul
      v-if="proposedChoiceTexts.length > 0"
      class="grid gap-1 text-sm text-navy"
      data-test="exam-workspace-proposal-choices"
    >
      <li
        v-for="text in proposedChoiceTexts"
        :key="text"
        class="border-l-4 border-action pl-2"
      >
        {{ text }}
      </li>
    </ul>

    <dl
      v-if="proposedGapValues.length > 0"
      class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm text-navy"
      data-test="exam-workspace-proposal-gaps"
    >
      <template
        v-for="gap in proposedGapValues"
        :key="gap.gapId"
      >
        <dt class="font-semibold">
          {{ gap.label }}
        </dt>
        <dd class="min-w-0 break-words">
          {{ gap.values }}
        </dd>
      </template>
    </dl>

    <div class="flex flex-wrap gap-2">
      <button
        type="button"
        class="btn-cta shadow-none"
        :disabled="disabled"
        data-test="exam-workspace-proposal-approve"
        @click="emit('approve', item.item_id)"
      >
        Godkänn förslaget
      </button>
      <button
        type="button"
        class="btn-ghost shadow-none"
        :disabled="disabled"
        data-test="exam-workspace-proposal-edit"
        @click="emit('edit', item.item_id)"
      >
        Redigera förslaget
      </button>
      <button
        type="button"
        class="btn-ghost shadow-none"
        :disabled="disabled"
        data-test="exam-workspace-proposal-dismiss"
        @click="emit('dismiss', item.item_id)"
      >
        Avvisa
      </button>
    </div>
  </section>
</template>
