<script setup lang="ts">
/**
 * Exam workspace question header.
 *
 * Domain purpose:
 *   "Fråga 3" and its type, which opens Byt frågetyp; "Gör om till [typ]"
 *   when the labeler suggests another type (`suggested_kind`), also marked
 *   Förslag in Byt frågetyp; Import, which shows the
 *   question as the exam file had it; the review check; and ⋮ with Flytta
 *   upp, Flytta ned, Flytta till… and Ta bort for a deluppgift, or Flytta
 *   till… and Ta bort for a question. Flytta till lists the parts and "Ingen
 *   del (fristående)", marking the question's current place and refusing a
 *   part for an ordering question (G3, G6). Deleting a part's last question
 *   keeps the part, so the entry needs no warning.
 *   A question that could not be converted shows its type in red. While the
 *   question still converts its type cannot change. Import and the review
 *   check come in through the `tools` slot (`ExamWorkspaceQuestionTools`);
 *   on a phone they move to the question strip.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionEditor`; emits every intent.
 */

import { computed, ref } from "vue";

import type { NativeExamItemKind } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import { EXAM_WORKSPACE_TYPE_LABELS } from "./examWorkspaceRows";

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
  }>(),
  { currentParentId: null, moveTargets: () => [] },
);

/** Ordering questions are standalone only (ST-SKRIPT-39-06 P3), so a deluppgift cannot change to Ordna. */
const orderedKinds = computed<QuestionTypeOption[]>(() =>
  KINDS.filter((option) => !(props.child !== null && option.kind === "ordering")),
);

const emit = defineEmits<{
  changeType: [kind: NativeExamItemKind];
  move: [delta: -1 | 1];
  remove: [];
  moveTo: [targetParentId: string | null];
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
      class="qhead__type"
      :class="{ 'qhead__type--error': unbuilt }"
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
      />{{ typeLabel }}<UiGlyph
        meaning="open-list"
        :size="16"
      />
    </button>
    <div class="qhead__tools">
      <button
        v-if="offeredKind"
        type="button"
        class="xw-btn xw-btn--compact"
        :disabled="converting || disabled"
        title="Byt till den typ som provfilen tyder på"
        data-test="exam-workspace-suggested-type"
        @click="emit('changeType', offeredKind)"
      >
        <UiGlyph
          meaning="convert-type"
          :size="16"
        />Gör om till {{ EXAM_WORKSPACE_TYPE_LABELS[offeredKind] }}
      </button>
      <span class="qhead__desk-tools">
        <slot name="tools" />
      </span>
      <button
        ref="moreTrigger"
        type="button"
        class="xw-btn xw-btn--icon xw-btn--ghost"
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
          :size="20"
        />
      </button>
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
        v-for="option in orderedKinds"
        :key="option.kind"
        type="button"
        class="xw-mi"
        role="menuitemradio"
        :aria-checked="!unbuilt && option.kind === kind"
        :data-test="`exam-workspace-type-${option.kind}`"
        @click="chooseKind(option.kind)"
      >
        <UiGlyph
          v-if="!unbuilt && option.kind === kind"
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
.qhead__type {
  all: unset; box-sizing: border-box; display: inline-flex; align-items: center; gap: var(--huleedu-space-1);
  height: 28px; min-width: 0; padding: 0 var(--huleedu-space-2); overflow: hidden; white-space: nowrap; cursor: pointer;
  border: 1px solid transparent; border-radius: var(--huleedu-workbench-control-radius);
  font-size: var(--huleedu-text-sm); color: var(--huleedu-navy-70);
}
.qhead__type:disabled { cursor: not-allowed; color: var(--huleedu-navy-40); }
.qhead__type[aria-expanded="true"] { border-color: var(--huleedu-action); background: var(--huleedu-action-10); color: var(--huleedu-action); }
.qhead__type--error { border-color: var(--huleedu-error); color: var(--huleedu-error); font-weight: var(--huleedu-font-medium); }
.qhead__type:focus-visible { outline: 2px solid var(--huleedu-action-40); }
@media (hover: hover) { .qhead__type:not(:disabled):hover { border-color: var(--huleedu-panel-border); } }
.qhead__tools { margin-left: auto; display: flex; align-items: center; gap: var(--huleedu-space-2); flex: none; }
.qhead__desk-tools { display: contents; }
.qhead__unbuilt { margin: -8px 0 12px; }
@media (max-width: 767px) {
  .qhead { padding-bottom: var(--huleedu-space-2); }
  .qhead__number { display: none; }
  .qhead__desk-tools { display: none; }
}
</style>
