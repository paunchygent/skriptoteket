<script setup lang="ts">
/**
 * Exam workspace instruction editor.
 *
 * Domain purpose:
 *   Edit an instruction with deluppgifter: the instruction text on the shared
 *   rich-text editor with the formatting toolbar (word-processor editing; an
 *   emptied instruction saves as empty and is not printed), and its
 *   deluppgifter in order, each opening the question, moving up or down, or
 *   being removed. "+ Deluppgift" adds a question of any kind last. The part line is the sum of the deluppgifter
 *   and says in amber when the exam text prints another part total; an
 *   instruction owns no points of its own.
 *
 *   Removing an instruction keeps its questions as standalone questions by
 *   default ("Ta bort instruktion"); removing it with every question is a
 *   separate entry lower in ⋮ (user ruling 2026-10-17). Removing the last
 *   deluppgift removes the emptied heading too. A removal the server refuses
 *   (the exam would have no question left) is said inline above the text.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceView` for a selected instruction; emits
 *     every intent; the view runs them through `useExamWorkspaceStructure`.
 */

import { computed, ref } from "vue";

import type { NativeExamBodyParagraph, NativeExamParent } from "../../../api/examWorkspace";
import type { ExamParentDeleteMode } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceInlineNotice from "./ExamWorkspaceInlineNotice.vue";
import ExamWorkspaceMarkToolbar from "./ExamWorkspaceMarkToolbar.vue";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import ExamWorkspaceNewItemMenu from "./ExamWorkspaceNewItemMenu.vue";
import ExamWorkspaceRichTextEntry from "./ExamWorkspaceRichTextEntry.vue";
import type { TeacherItemKind } from "./examWorkspaceItemEdits";
import type { ExamWorkspaceItemEntry } from "./examWorkspaceListEntries";
import { examWorkspaceFormatPoints, examWorkspacePointsLine } from "./examWorkspaceTotals";
import { provideRichTextTargetRegistry } from "./examWorkspaceRichTextTarget";
import type { RichTextHeadingLevel } from "./examWorkspaceRichTextTarget";
import type { BodyMark } from "./examWorkspaceBodyMarks";
import type { ExamWorkspaceNotice } from "./useExamWorkspaceStructure";

defineProps<{
  parent: NativeExamParent;
  label: string;
  children: ExamWorkspaceItemEntry[];
  subtotal: number;
  /** The part total the exam text prints, only when it differs from `subtotal`. */
  printedTotal: number | null;
  disabled: boolean;
  /** The last command's inline outcome, e.g. a refused delete. */
  notice: ExamWorkspaceNotice | null;
  /** Picture URLs by asset id, so a declared picture in the instruction renders. */
  assetUrls?: Record<string, string>;
}>();

const emit = defineEmits<{
  updateInstruction: [body: NativeExamBodyParagraph[], structural: boolean];
  gotoChild: [itemId: string];
  moveChild: [itemId: string, delta: -1 | 1];
  deleteChild: [itemId: string];
  addChild: [kind: TeacherItemKind];
  deleteParent: [mode: ExamParentDeleteMode];
  dismissNotice: [];
  acceptPartTotal: [];
}>();

const targets = provideRichTextTargetRegistry();
const activeMarks = computed(() => targets.active.value?.marks.value ?? []);
const activeHeading = computed(() => targets.active.value?.headingLevel() ?? null);

const addTrigger = ref<HTMLButtonElement | null>(null);
const moreTrigger = ref<HTMLButtonElement | null>(null);
const addOpen = ref(false);
const moreOpen = ref(false);

function toggleMark(mark: BodyMark): void {
  targets.active.value?.toggleMark(mark);
}

function toggleHeading(level: RichTextHeadingLevel): void {
  targets.active.value?.toggleHeading(level);
}

function chooseDelete(mode: ExamParentDeleteMode): void {
  moreOpen.value = false;
  emit("deleteParent", mode);
}
</script>

<template>
  <section
    class="ied"
    :aria-label="`Redigera instruktion ${label}`"
    data-test="exam-workspace-instruction-editor"
  >
    <div class="ied__head">
      <h1 class="ied__number">
        Fråga {{ label }}
      </h1>
      <span class="ied__type">Instruktion</span>
      <button
        ref="moreTrigger"
        type="button"
        class="xw-btn xw-btn--icon xw-btn--ghost ied__more"
        :disabled="disabled"
        aria-haspopup="menu"
        :aria-expanded="moreOpen"
        aria-label="Fler åtgärder"
        title="Fler åtgärder"
        data-test="exam-workspace-instruction-more"
        @click="moreOpen = !moreOpen"
      >
        <UiGlyph
          meaning="more-actions"
          :size="20"
        />
      </button>
    </div>

    <ExamWorkspaceInlineNotice
      v-if="notice"
      :notice="notice"
      @dismiss="emit('dismissNotice')"
    />
    <div class="xw-label ied__first">
      Instruktion
    </div>
    <div class="xw-rich">
      <ExamWorkspaceMarkToolbar
        class="xw-rich__bar"
        :active-marks="activeMarks"
        :active-heading="activeHeading"
        :disabled="disabled"
        show-headings
        @toggle-mark="toggleMark"
        @toggle-heading="toggleHeading"
      />
      <ExamWorkspaceRichTextEntry
        :key="parent.parent_id"
        class="xw-rich__body"
        :body="parent.instruction"
        :disabled="disabled"
        label="Instruktion"
        test-id="exam-workspace-instruction-text"
        variant="paragraph"
        :asset-urls="assetUrls"
        @update-body="(body, structural) => emit('updateInstruction', body, structural)"
      />
    </div>

    <div class="xw-label">
      <span class="xw-grow">Deluppgifter</span>
      <button
        ref="addTrigger"
        type="button"
        class="xw-btn xw-btn--compact"
        :disabled="disabled"
        aria-haspopup="menu"
        :aria-expanded="addOpen"
        data-test="exam-workspace-add-child"
        @click="addOpen = !addOpen"
      >
        <UiGlyph
          meaning="add"
          :size="16"
        />Deluppgift
      </button>
    </div>
    <ol
      class="kids"
      data-test="exam-workspace-children"
    >
      <li
        v-for="(entry, index) in children"
        :key="entry.id"
        class="kid"
      >
        <span class="xw-muted kid__n">{{ entry.label }}</span>
        <button
          type="button"
          class="kid__open"
          :data-test="`exam-workspace-child-${entry.id}`"
          @click="emit('gotoChild', entry.id)"
        >
          <span class="kid__text">{{ entry.text || "Ny fråga" }}</span>
          <span class="kid__meta">{{ entry.typeLabel }}</span>
        </button>
        <span class="kid__pts">{{ entry.points === null ? "–" : examWorkspaceFormatPoints(entry.points) }} p</span>
        <span class="kid__ctl">
          <button
            type="button"
            class="xw-rm"
            :disabled="disabled || index === 0"
            aria-label="Flytta upp"
            title="Flytta upp"
            :data-test="`exam-workspace-child-up-${entry.id}`"
            @click="emit('moveChild', entry.id, -1)"
          >
            <UiGlyph
              meaning="move-up"
              :size="16"
            />
          </button>
          <button
            type="button"
            class="xw-rm"
            :disabled="disabled || index === children.length - 1"
            aria-label="Flytta ned"
            title="Flytta ned"
            :data-test="`exam-workspace-child-down-${entry.id}`"
            @click="emit('moveChild', entry.id, 1)"
          >
            <UiGlyph
              meaning="move-down"
              :size="16"
            />
          </button>
          <button
            type="button"
            class="xw-rm"
            :disabled="disabled"
            aria-label="Ta bort deluppgiften"
            :title="children.length === 1 ? 'Ta bort deluppgiften och instruktionen' : 'Ta bort deluppgiften'"
            :data-test="`exam-workspace-child-delete-${entry.id}`"
            @click="emit('deleteChild', entry.id)"
          >
            <UiGlyph
              meaning="delete"
              :size="16"
            />
          </button>
        </span>
      </li>
    </ol>
    <p class="psum">
      <span
        class="psum__points"
        :class="{ 'psum__points--printed': printedTotal !== null }"
        data-test="exam-workspace-part-points"
      >{{ examWorkspacePointsLine(subtotal, printedTotal) }}</span>
      <button
        v-if="printedTotal !== null"
        type="button"
        class="xw-btn xw-btn--compact xw-btn--ghost"
        :disabled="disabled"
        data-test="exam-workspace-accept-part-total"
        @click="emit('acceptPartTotal')"
      >
        Använd {{ examWorkspaceFormatPoints(subtotal) }} p
      </button>
      <span>Poängen sätts på varje deluppgift.</span>
    </p>

    <ExamWorkspaceNewItemMenu
      :open="addOpen"
      :anchor="addTrigger"
      :child="true"
      @choose="(kind) => kind !== 'instruction' && kind !== 'part' && emit('addChild', kind)"
      @close="addOpen = false"
    />
    <ExamWorkspaceMenu
      :open="moreOpen"
      :anchor="moreTrigger"
      label="Fler åtgärder"
      test-id="exam-workspace-instruction-more-menu"
      @close="moreOpen = false"
    >
      <button
        type="button"
        class="xw-mi"
        role="menuitem"
        data-test="exam-workspace-delete-instruction"
        @click="chooseDelete('keep_questions')"
      >
        <UiGlyph
          meaning="delete"
          :size="20"
        /><span class="xw-mi__stack"><span>Ta bort instruktion</span><span class="xw-mi__sub">Frågorna blir kvar som egna frågor</span></span>
      </button>
      <div class="xw-mdiv" />
      <button
        type="button"
        class="xw-mi"
        role="menuitem"
        data-test="exam-workspace-delete-instruction-with-children"
        @click="chooseDelete('with_questions')"
      >
        <span class="xw-mi__pad" /><span class="xw-grow">Ta bort instruktion och alla dess frågor</span>
      </button>
    </ExamWorkspaceMenu>
  </section>
</template>

<style scoped>
.ied { display: flex; flex-direction: column; min-width: 0; }
.ied__head { display: flex; align-items: center; gap: var(--huleedu-space-2); padding-bottom: var(--huleedu-space-4); }
.ied__number { margin: 0; font-size: var(--huleedu-text-lg); font-weight: var(--huleedu-font-semibold); white-space: nowrap; }
.ied__type { padding: 0 var(--huleedu-space-2); font-size: var(--huleedu-text-sm); color: var(--huleedu-navy-70); }
.ied__more { margin-left: auto; }
.ied .ied__first { margin-top: 0; }
.kids { margin: 0; padding: 0; list-style: none; border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg); }
.kid {
  display: grid; grid-template-columns: 32px minmax(0, 1fr) auto auto; align-items: center; gap: var(--huleedu-space-2);
  padding: var(--huleedu-space-1-5) var(--huleedu-space-2) var(--huleedu-space-1-5) var(--huleedu-space-3);
}
.kid + .kid { border-top: 1px solid var(--huleedu-surface-divider); }
.kid__n { font-size: var(--huleedu-text-sm); }
.kid__open {
  all: unset; box-sizing: border-box; display: flex; flex-direction: column; min-width: 0; padding: var(--huleedu-space-1) 0;
  cursor: pointer;
}
.kid__open:focus-visible { outline: 2px solid var(--huleedu-action-40); }
.kid__text { font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-medium); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kid__meta { font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60); }
@media (hover: hover) { .kid__open:hover .kid__text { color: var(--huleedu-action); text-decoration: underline; } }
.kid__pts { font-size: var(--huleedu-text-sm); white-space: nowrap; }
.kid__ctl { display: flex; gap: 2px; }
.psum {
  display: flex; flex-wrap: wrap; gap: var(--huleedu-space-2) var(--huleedu-space-4); margin: var(--huleedu-space-3) 0 0;
  font-size: var(--huleedu-text-sm); color: var(--huleedu-navy-70);
}
.psum__points { font-weight: var(--huleedu-font-semibold); color: var(--huleedu-navy); overflow-wrap: anywhere; }
.psum__points--printed { color: var(--huleedu-warning); }
@media (max-width: 767px) {
  .ied__number { display: none; }
  .kid { grid-template-columns: 28px minmax(0, 1fr) auto; }
  .kid__ctl { grid-column: 2 / -1; justify-content: flex-end; }
}
</style>
