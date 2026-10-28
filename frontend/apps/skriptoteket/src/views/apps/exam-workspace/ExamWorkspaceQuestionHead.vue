<script setup lang="ts">
/**
 * Exam workspace question header.
 *
 * Domain purpose:
 *   "Fråga 3" and its compact type button, which opens Byt frågetyp; the
 *   type the labeler suggests (`suggested_kind`) is marked Förslag there,
 *   and "Byt till [typ]" lives in the question-text toolbar's AI group;
 *   Import, which shows the
 *   question as the exam file had it; the review check; and ⋮ with Flytta
 *   upp, Flytta ned, Flytta till… and Ta bort for a deluppgift, or Flytta
 *   till… and Ta bort for a question. Flytta till lists the parts and "Ingen
 *   del (fristående)", marking the question's current place and refusing a
 *   part for an ordering question (G3, G6). Deleting a part's last question
 *   keeps the part, so the entry needs no warning.
 *   On a phone or touch device the same ⋮ menu opens with the question's
 *   three AI controls as words above the built rows, then a separator
 *   (TASK-SKRIPT-40-04-26 D7, D8): a menu row has no tooltip and touch has no
 *   hover. The rows always render and the stylesheet decides where they show.
 *   Their states are the editor's one computed state, so the toolbar group
 *   and these rows cannot disagree. The rows themselves are
 *   `ExamWorkspaceQuestionAiMenuRows`, which closes nothing and emits its
 *   intent here; each emit closes the menu and re-emits the question intent.
 *   A question that could not be converted shows its type in red. While the
 *   question still converts its type cannot change. Import and the review
 *   check come in through the `tools` slot (`ExamWorkspaceQuestionTools`);
 *   on a phone they move to the question strip.
 *   Byt frågetyp lists Kort svar after Fritext when the question is a Kort
 *   svar or may become one: a Kort svar ticks Kort svar and unticks
 *   Lucktext, and choosing Lucktext there emits `changeShape`; an eligible
 *   Lucktext ticks Lucktext and offers Kort svar unticked instead.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor`; emits every intent.
 */

import { computed, ref } from "vue";

import type { NativeExamItemKind } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import ExamWorkspaceQuestionAiMenuRows from "./ExamWorkspaceQuestionAiMenuRows.vue";
import type { QuestionAiControls } from "./examWorkspaceQuestionAi";
import { EXAM_WORKSPACE_TYPE_LABELS } from "./examWorkspaceRows";
import type { ExamWorkspaceItemShape } from "./examWorkspaceShortAnswer";

const PROTOTYPE_KIND_ORDER: NativeExamItemKind[] = [
  "free_text",
  "single_choice",
  "multiple_response",
  "gap_fill",
  "inline_choice",
  "matching",
  "ordering",
];

type QuestionTypeOption = { kind: NativeExamItemKind; label: string };

const KINDS: QuestionTypeOption[] = PROTOTYPE_KIND_ORDER.map((kind) => ({
  kind,
  label: EXAM_WORKSPACE_TYPE_LABELS[kind],
}));

const props = withDefaults(
  defineProps<{
    label: string;
    kind: NativeExamItemKind;
    unbuilt: boolean;
    converting: boolean;
    /** Where a deluppgift sits in its instruction; null for a standalone question. */
    child: { index: number; count: number } | null;
    disabled: boolean;
    /** The type the labeler suggests for this question; null when it has none. */
    suggestedKind: NativeExamItemKind | null;
    /** The places Flytta till offers, in list order, each with its display label. */
    moveTargets?: { id: string; label: string }[];
    /** The part the question sits in; null when it is standalone. */
    currentParentId?: string | null;
    /** The visible type button text: "Kort svar" for that shape, else the kind label. */
    typeLabel: string;
    /** True when the question is a Kort svar (a Lucktext whose only gap stands alone). */
    shortAnswer?: boolean;
    /** True when a Lucktext with at most one gap may become a Kort svar. */
    shortAnswerOffered?: boolean;
    /** The question's AI controls, the same state the toolbar group reads; null when not shown. */
    aiControls?: QuestionAiControls;
  }>(),
  {
    aiControls: () => ({ convert: null, suggest: null, undo: null }),
    currentParentId: null,
    moveTargets: () => [],
    shortAnswer: false,
    shortAnswerOffered: false,
  },
);

/** Ordering questions are standalone only (ST-SKRIPT-39-06 P3), so a deluppgift cannot change to Ordna. */
const orderedKinds = computed<QuestionTypeOption[]>(() =>
  KINDS.filter((option) => !(props.child !== null && option.kind === "ordering")),
);

/** One Byt frågetyp entry: a native kind, or the Kort svar shape. */
type TypeMenuEntry = { checked: boolean; kind: NativeExamItemKind | "short_answer"; label: string };

/**
 * Byt frågetyp lists Fritext, then Kort svar when the question is one or may
 * become one, then the remaining kinds as today. A Kort svar ticks Kort svar
 * and unticks Lucktext; a kind ticks when it matches and the question is
 * neither unbuilt nor a Kort svar Lucktext.
 */
const menuEntries = computed<TypeMenuEntry[]>(() => {
  const shortAnswerEntry: TypeMenuEntry = { checked: props.shortAnswer, kind: "short_answer", label: "Kort svar" };
  const entries = orderedKinds.value.flatMap((option, index) => {
    const entry: TypeMenuEntry = {
      checked:
        !props.unbuilt &&
        option.kind === props.kind &&
        !(props.shortAnswer && option.kind === "gap_fill"),
      kind: option.kind,
      label: option.label,
    };
    if (index === 0 && (props.shortAnswer || props.shortAnswerOffered)) {
      return [entry, shortAnswerEntry];
    }
    return [entry];
  });
  return entries;
});

const emit = defineEmits<{
  changeType: [kind: NativeExamItemKind];
  changeShape: [shape: ExamWorkspaceItemShape];
  move: [delta: -1 | 1];
  remove: [];
  moveTo: [targetParentId: string | null];
  aiSuggest: [];
  aiUndo: [];
  aiConvert: [kind: NativeExamItemKind];
}>();

const typeTrigger = ref<HTMLButtonElement | null>(null);
const moreTrigger = ref<HTMLButtonElement | null>(null);
const typeOpen = ref(false);
const moreOpen = ref(false);
const moveOpen = ref(false);

/** Offered while the question has another type, or has not been converted at all. */
const offeredKind = computed(() =>
  props.suggestedKind !== null && (props.suggestedKind !== props.kind || props.unbuilt) ? props.suggestedKind : null,
);

/** An ordering question is never a part member (G6). */
const ORDERING_REASON = "Ordna-frågor kan inte ligga i en del";

/** The entry's refusal in a few words, or null when the question may move there. */
function targetHint(targetParentId: string | null): string | null {
  if (targetParentId === props.currentParentId) {
    return "Här nu";
  }
  if (props.kind === "ordering" && targetParentId !== null) {
    return ORDERING_REASON;
  }
  return null;
}

/** The Flytta till entries: "Ingen del (fristående)" first, then every part in list order (G3). */
type MoveOption = { hint: string | null; id: string | null; label: string };

const moveOptions = computed<MoveOption[]>(() => [
  { hint: targetHint(null), id: null, label: "Ingen del (fristående)" },
  ...props.moveTargets.map<MoveOption>((target) => ({ hint: targetHint(target.id), id: target.id, label: target.label })),
]);

/**
 * Close ⋮ Fler åtgärder and re-emit an AI row's intent; a disabled row never
 * reaches here, because `ExamWorkspaceQuestionAiMenuRows` emits nothing.
 */
function chooseAiIntent(action: "suggest" | "undo" | "convert", kind?: NativeExamItemKind): void {
  moreOpen.value = false;
  if (action === "suggest") {
    emit("aiSuggest");
  } else if (action === "undo") {
    emit("aiUndo");
  } else if (kind !== undefined) {
    emit("aiConvert", kind);
  }
}

function openMove(): void {
  moreOpen.value = false;
  moveOpen.value = true;
}

function chooseMove(targetParentId: string | null): void {
  if (targetHint(targetParentId) !== null) {
    return;
  }
  moveOpen.value = false;
  emit("moveTo", targetParentId);
}

function chooseKind(kind: NativeExamItemKind): void {
  typeOpen.value = false;
  if (kind !== props.kind || props.unbuilt) {
    emit("changeType", kind);
  }
}

/**
 * One Byt frågetyp choice: Kort svar switches shape without a server change
 * type (choosing it on a Kort svar does nothing), and so does Lucktext on a
 * Kort svar; everything else follows `chooseKind`.
 */
function chooseOption(kind: NativeExamItemKind | "short_answer"): void {
  if (kind === "short_answer") {
    typeOpen.value = false;
    if (!props.shortAnswer) {
      emit("changeShape", "short_answer");
    }
    return;
  }
  if (props.shortAnswer && kind === "gap_fill") {
    typeOpen.value = false;
    emit("changeShape", "gap_fill");
    return;
  }
  chooseKind(kind);
}

function chooseMore(action: "up" | "down" | "remove"): void {
  moreOpen.value = false;
  if (action === "remove") {
    emit("remove");
  } else {
    emit("move", action === "up" ? -1 : 1);
  }
}
</script>

<template>
  <div class="qhead">
    <h1 class="qhead__number">
      Fråga {{ label }}
    </h1>
    <button
      ref="typeTrigger"
      type="button"
      class="xw-btn xw-btn--compact qhead__kind"
      :class="{ 'qhead__kind--error': unbuilt }"
      :disabled="converting || disabled"
      aria-haspopup="menu"
      :aria-expanded="typeOpen"
      title="Byt frågetyp"
      data-test="exam-workspace-type"
      @click="typeOpen = !typeOpen"
    >
      <UiGlyph
        v-if="unbuilt"
        meaning="blocker"
        :size="16"
      /><span class="qhead__kindtext">{{ typeLabel }}</span><UiGlyph
        meaning="open-list"
        :size="16"
      />
    </button>
    <div class="qhead__tools">
      <span class="xw-tools">
        <span class="qhead__desk-tools">
          <slot name="tools" />
        </span>
        <button
          ref="moreTrigger"
          type="button"
          class="xw-tool"
          :disabled="disabled"
          aria-haspopup="menu"
          :aria-expanded="moreOpen"
          aria-label="Fler åtgärder"
          title="Fler åtgärder"
          data-test="exam-workspace-more"
          @click="moreOpen = !moreOpen"
        >
          <UiGlyph
            meaning="more-actions"
            :size="16"
          />
        </button>
      </span>
    </div>

    <ExamWorkspaceMenu
      :open="typeOpen"
      :anchor="typeTrigger"
      align="left"
      label="Byt frågetyp"
      test-id="exam-workspace-type-menu"
      @close="typeOpen = false"
    >
      <div class="xw-mhead">
        Byt frågetyp
      </div>
      <button
        v-for="option in menuEntries"
        :key="option.kind"
        type="button"
        class="xw-mi"
        role="menuitemradio"
        :aria-checked="option.checked"
        :data-test="`exam-workspace-type-${option.kind}`"
        @click="chooseOption(option.kind)"
      >
        <UiGlyph
          v-if="option.checked"
          meaning="selected"
          :size="20"
        /><span
          v-else
          class="xw-mi__pad"
        /><span class="xw-grow">{{ option.label }}</span><span
          v-if="option.kind === offeredKind"
          class="xw-chip xw-chip--teal"
          data-test="exam-workspace-type-suggested"
        ><UiGlyph
          meaning="convert-type"
          :size="12"
        />Förslag</span>
      </button>
    </ExamWorkspaceMenu>

    <ExamWorkspaceMenu
      :open="moreOpen"
      :anchor="moreTrigger"
      label="Fler åtgärder"
      test-id="exam-workspace-more-menu"
      @close="moreOpen = false"
    >
      <ExamWorkspaceQuestionAiMenuRows
        :controls="aiControls"
        @suggest="chooseAiIntent('suggest')"
        @undo="chooseAiIntent('undo')"
        @convert="(kind) => chooseAiIntent('convert', kind)"
      />
      <template v-if="child">
        <button
          type="button"
          class="xw-mi"
          role="menuitem"
          :aria-disabled="child.index === 0 || undefined"
          data-test="exam-workspace-move-up"
          @click="child.index > 0 && chooseMore('up')"
        >
          <UiGlyph
            meaning="move-up"
            :size="20"
          /><span class="xw-grow">Flytta upp</span>
        </button>
        <button
          type="button"
          class="xw-mi"
          role="menuitem"
          :aria-disabled="child.index === child.count - 1 || undefined"
          data-test="exam-workspace-move-down"
          @click="child.index < child.count - 1 && chooseMore('down')"
        >
          <UiGlyph
            meaning="move-down"
            :size="20"
          /><span class="xw-grow">Flytta ned</span>
        </button>
        <div class="xw-mdiv" />
      </template>
      <button
        type="button"
        class="xw-mi"
        role="menuitem"
        data-test="exam-workspace-move-to"
        @click="openMove"
      >
        <UiGlyph
          meaning="open-detail"
          :size="20"
        /><span class="xw-grow">Flytta till…</span>
      </button>
      <button
        type="button"
        class="xw-mi"
        role="menuitem"
        data-test="exam-workspace-delete"
        @click="chooseMore('remove')"
      >
        <UiGlyph
          meaning="delete"
          :size="20"
        /><span class="xw-grow">{{ child ? "Ta bort deluppgiften" : "Ta bort frågan" }}</span>
      </button>
    </ExamWorkspaceMenu>

    <ExamWorkspaceMenu
      :open="moveOpen"
      :anchor="moreTrigger"
      label="Flytta till"
      test-id="exam-workspace-move-menu"
      @close="moveOpen = false"
    >
      <div class="xw-mhead">
        Flytta till
      </div>
      <button
        v-for="option in moveOptions"
        :key="option.id ?? 'standalone'"
        type="button"
        class="xw-mi"
        role="menuitem"
        :aria-disabled="option.hint !== null || undefined"
        :data-test="option.id === null ? 'exam-workspace-move-standalone' : `exam-workspace-move-${option.id}`"
        @click="chooseMove(option.id)"
      >
        <span class="xw-mi__pad" /><span class="xw-grow">{{ option.label }}</span><span
          v-if="option.hint"
          class="xw-mi__hint"
        >{{ option.hint }}</span>
      </button>
    </ExamWorkspaceMenu>
  </div>
  <p
    v-if="unbuilt"
    class="xw-errline qhead__unbuilt"
  >
    <UiGlyph
      meaning="blocker"
      :size="16"
    />Frågan kunde inte konverteras och visas som i provfilen. Välj typ eller markera den som granskad.
  </p>
</template>

<style scoped>
.qhead { display: flex; align-items: center; gap: var(--huleedu-space-2); min-width: 0; padding-bottom: var(--huleedu-space-4); }
.qhead__number { margin: 0; font-size: var(--huleedu-text-lg); font-weight: var(--huleedu-font-semibold); white-space: nowrap; }
/* The trigger is a built compact button; these rules only let it shrink and truncate its name. */
.qhead__kind { flex: 0 1 auto; min-width: 0; overflow: hidden; }
.qhead__kindtext { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.qhead__kind--error { border-color: var(--huleedu-error); color: var(--huleedu-error); }
.qhead__tools { margin-left: auto; display: flex; align-items: center; gap: var(--huleedu-space-2); flex: none; }
.qhead__desk-tools { display: contents; }
.qhead__unbuilt { margin: -8px 0 12px; }
@media (max-width: 767px) {
  .qhead { padding-bottom: var(--huleedu-space-2); }
  .qhead__number { display: none; }
  .qhead__desk-tools { display: none; }
}
</style>
