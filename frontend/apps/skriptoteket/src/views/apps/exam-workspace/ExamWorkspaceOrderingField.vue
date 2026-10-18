<script setup lang="ts">
/**
 * Exam workspace ordering field.
 *
 * Domain purpose:
 *   Edit an ordering question's steps. The steps are listed in the answer-key
 *   order (the list order is the key, TASK-SKRIPT-39-06-08 D1), each as one
 *   rich-text entry with move up, move down and remove. "Lägg till steg" adds
 *   an empty step at the end. Below the list "Utskriftsordning" shows the
 *   saved print order exactly as printed, each step after an empty number box
 *   the student fills in, and "Blanda om" asks for a new one. A step whose
 *   body carries no text still saves and is marked, because export refuses it. While
 *   `disabled` is set, every control is disabled.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor` for ordering questions.
 *   - Emits typed events; `useExamWorkspaceItemEdits` applies the transitions
 *     from `examWorkspaceOrdering` through the document's item patch path.
 */

import { computed, useId } from "vue";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceRichTextEntry from "./ExamWorkspaceRichTextEntry.vue";
import { bodyText } from "./examWorkspaceRichText";

const props = defineProps<{
  disabled?: boolean;
  item: NativeExamItem;
}>();

const emit = defineEmits<{
  addStep: [];
  moveStep: [choiceId: string, delta: -1 | 1];
  removeStep: [choiceId: string];
  shuffle: [];
  updateBody: [choiceId: string, body: NativeExamBodyParagraph[], structural: boolean];
}>();

const EMPTY_STEP_GUIDANCE = "Ett steg saknar text.";

const hintId = useId();
const stepHintId = useId();

const printedSteps = computed(() =>
  props.item.print_order.flatMap((choiceId) => {
    const choice = props.item.choices.find((candidate) => candidate.choice_id === choiceId);
    return choice ? [choice] : [];
  }),
);
/** The rule the export blocker uses: a step without non-whitespace text is empty. */
function isEmptyStep(body: NativeExamBodyParagraph[]): boolean {
  return bodyText(body).length === 0;
}

const hasEmptyStep = computed(() => props.item.choices.some((choice) => isEmptyStep(choice.body)));
const onlyStep = computed(() => props.item.choices.length <= 1);
</script>

<template>
  <fieldset
    v-if="item.kind === 'ordering'"
    class="ord"
    data-test="exam-workspace-ordering-field"
  >
    <legend class="mb-1 text-xs font-semibold text-navy/80">
      Steg i rätt ordning
    </legend>
    <p
      :id="hintId"
      class="xw-hint ord__hint"
    >
      Skriv stegen i rätt ordning. Ordningen i listan är facit.
    </p>
    <div
      v-for="(choice, index) in item.choices"
      :key="choice.choice_id"
      class="ord__row"
    >
      <span
        class="ord__num"
        aria-hidden="true"
      >{{ index + 1 }}</span>
      <ExamWorkspaceRichTextEntry
        :key="`${item.item_id}-${choice.choice_id}`"
        :body="choice.body"
        :border-class="isEmptyStep(choice.body) ? 'border-warning' : 'border-navy/35'"
        :described-by="isEmptyStep(choice.body) ? stepHintId : hintId"
        :disabled="disabled"
        :invalid="isEmptyStep(choice.body)"
        :label="`Text för steg ${index + 1}`"
        :test-id="`exam-workspace-ordering-step-text-${choice.choice_id}`"
        @update-body="(body, structural) => emit('updateBody', choice.choice_id, body, structural)"
      />
      <div class="ord__actions">
        <button
          type="button"
          class="xw-btn xw-btn--icon xw-btn--compact xw-btn--ghost"
          :aria-label="`Flytta upp steg ${index + 1}`"
          title="Flytta upp"
          :disabled="disabled || index === 0"
          :data-test="`exam-workspace-ordering-step-up-${choice.choice_id}`"
          @click="emit('moveStep', choice.choice_id, -1)"
        >
          <UiGlyph
            meaning="move-up"
            :size="16"
          />
        </button>
        <button
          type="button"
          class="xw-btn xw-btn--icon xw-btn--compact xw-btn--ghost"
          :aria-label="`Flytta ned steg ${index + 1}`"
          title="Flytta ned"
          :disabled="disabled || index === item.choices.length - 1"
          :data-test="`exam-workspace-ordering-step-down-${choice.choice_id}`"
          @click="emit('moveStep', choice.choice_id, 1)"
        >
          <UiGlyph
            meaning="move-down"
            :size="16"
          />
        </button>
        <button
          type="button"
          class="xw-btn xw-btn--icon xw-btn--compact xw-btn--ghost"
          :aria-label="`Ta bort steg ${index + 1}`"
          title="Ta bort steg"
          :disabled="disabled || onlyStep"
          :data-test="`exam-workspace-ordering-step-remove-${choice.choice_id}`"
          @click="emit('removeStep', choice.choice_id)"
        >
          <UiGlyph
            meaning="remove-item"
            :size="16"
          />
        </button>
      </div>
    </div>
    <p
      v-if="hasEmptyStep"
      :id="stepHintId"
      class="ord__warn"
      data-test="exam-workspace-ordering-empty-hint"
    >
      {{ EMPTY_STEP_GUIDANCE }}
    </p>
    <div>
      <button
        type="button"
        class="xw-btn xw-btn--compact"
        :disabled="disabled"
        data-test="exam-workspace-ordering-add-step"
        @click="emit('addStep')"
      >
        <UiGlyph
          meaning="add"
          :size="16"
        />Lägg till steg
      </button>
    </div>

    <div class="ord__print">
      <div class="ord__print-head">
        <span class="text-xs font-semibold text-navy/80">Utskriftsordning</span>
        <button
          type="button"
          class="xw-btn xw-btn--compact"
          :disabled="disabled || item.choices.length < 2"
          data-test="exam-workspace-ordering-shuffle"
          @click="emit('shuffle')"
        >
          <UiGlyph
            meaning="shuffle"
            :size="16"
          />Blanda om
        </button>
      </div>
      <ol
        class="ord__list"
        data-test="exam-workspace-ordering-print-order"
      >
        <li
          v-for="choice in printedSteps"
          :key="choice.choice_id"
          class="ord__printed"
          :data-test="`exam-workspace-ordering-printed-${choice.choice_id}`"
        >
          <span
            class="ord__box"
            aria-hidden="true"
          /><span>{{ bodyText(choice.body) }}</span>
        </li>
      </ol>
    </div>
  </fieldset>
</template>

<style scoped>
.ord { display: grid; gap: var(--huleedu-space-2); min-width: 0; border: 0; padding: 0; margin: 0; }
.ord__hint { margin: 0 0 var(--huleedu-space-1); }
.ord__row { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: start; gap: var(--huleedu-space-2); }
.ord__num { margin-top: var(--huleedu-space-2); width: 20px; text-align: center; font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-medium); color: var(--huleedu-navy-70); }
.ord__actions { display: flex; gap: var(--huleedu-space-1); }
.ord__warn { margin: 0; padding-left: var(--huleedu-space-2); border-left: 4px solid var(--huleedu-warning); font-size: var(--huleedu-text-sm); }
.ord__print { margin-top: var(--huleedu-space-3); padding: var(--huleedu-space-3); border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg); background: var(--huleedu-navy-02); }
.ord__print-head { display: flex; align-items: center; justify-content: space-between; gap: var(--huleedu-space-2); margin-bottom: var(--huleedu-space-2); }
.ord__list { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--huleedu-space-2); font-family: var(--huleedu-font-serif); font-size: var(--huleedu-text-sm); }
.ord__printed { display: flex; align-items: baseline; gap: var(--huleedu-space-2); }
.ord__box { flex: none; width: 22px; height: 22px; border: 1px solid var(--huleedu-navy-60); background: var(--huleedu-surface-content); }
</style>
