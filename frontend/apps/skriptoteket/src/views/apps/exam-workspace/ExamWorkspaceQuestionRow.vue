<script setup lang="ts">
/**
 * Exam workspace question list row.
 *
 * Domain purpose:
 *   One entry of the question list: its number, the start of its text and
 *   one line naming its type and points, or the first thing that stops its
 *   export in red. A question shows whether the AI wrote its key and whether
 *   it is reviewed, needs review or still converts. An instruction row shows
 *   how many deluppgifter it holds on its second line and their plain points
 *   on a third line of fixed height, like every other row; a printed-total
 *   difference lives only in the footer's points note. Its
 *   deluppgifter are indented under it. A part with no questions is an
 *   unnumbered instruction block: its text or "Tom instruktion", the meta
 *   "Instruktion utan frågor" and no points. In Markera mode a standalone
 *   question carries a checkbox; a part and a question inside a part do not.
 *
 * Relationships:
 *   - A `row` of the list's grid: every child is a `gridcell`.
 *   - Rendered by `ExamWorkspaceQuestionList`; receives `selected` as a
 *     boolean, so moving the selection re-renders only the two rows involved.
 */

import { computed } from "vue";

import { UiGlyph } from "../../../components/ui";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { examWorkspaceFormatPoints } from "./examWorkspaceTotals";

const props = defineProps<{
  entry: ExamWorkspaceListEntry;
  selected: boolean;
  disabled: boolean;
  /** The list is in Markera mode: a standalone question carries a checkbox. */
  marking: boolean;
  /** The teacher has ticked this row. */
  marked: boolean;
  /** The question's points differ from the source: its points show amber. */
  pointsDiffer: boolean;
}>();

const emit = defineEmits<{
  select: [id: string];
  toggleMark: [id: string];
}>();

/** A part with no questions is an unnumbered instruction block, not a scored unit (G5, R1). */
const childlessPart = computed(() => props.entry.kind === "parent" && props.entry.childIds.length === 0);
/** Only a standalone question takes a mark; a question inside a part moves with Flytta till (G11). */
const markable = computed(() => props.entry.kind === "item" && props.entry.parentId === null);
/** An ordering question can never join a part (G6), so its checkbox is disabled with the reason. */
const ordering = computed(
  () => props.entry.kind === "item" && props.entry.parentId === null && props.entry.itemKind === "ordering",
);

const rowText = computed(() => props.entry.text || (childlessPart.value ? "Tom instruktion" : "Ny fråga"));

const meta = computed(() => {
  const entry = props.entry;
  if (entry.kind === "parent") {
    if (childlessPart.value) {
      return "Instruktion utan frågor";
    }
    const count = entry.childIds.length;
    return `Instruktion · ${count} ${count === 1 ? "fråga" : "frågor"}`;
  }
  if (entry.status === "converting") {
    return "Konverteras …";
  }
  return entry.points === null ? entry.typeLabel : `${entry.typeLabel} · ${examWorkspaceFormatPoints(entry.points)} p`;
});

const aiTitle = computed(() =>
  props.entry.kind === "item" && props.entry.aiKey === "interpreted" ? "Tolkad av AI" : "Förslag från AI",
);

/** An ordering question is never a part member (G6); the checkbox says why it cannot be grouped. */
const ORDERING_REASON = "Ordna-frågor kan inte ligga i en del";
</script>

<template>
  <div
    class="row"
    :class="{
      'row--selected': selected,
      'row--parent': entry.kind === 'parent',
      'row--child': entry.kind === 'item' && entry.parentId !== null,
      'row--converting': entry.kind === 'item' && entry.status === 'converting',
    }"
    role="row"
    :aria-selected="selected"
    :tabindex="selected ? 0 : -1"
    :data-entry-id="entry.id"
    :data-test="`exam-workspace-row-${entry.id}`"
    @click="emit('select', entry.id)"
  >
    <span
      class="row__mark"
      :class="{ 'row__mark--idle': !marking }"
      role="gridcell"
    >
      <input
        v-if="markable"
        type="checkbox"
        class="h-5 w-5 accent-navy"
        :checked="marked"
        :disabled="disabled || ordering"
        :title="ordering ? ORDERING_REASON : undefined"
        :aria-label="`Markera fråga ${entry.label}`"
        :data-test="`exam-workspace-mark-${entry.id}`"
        @click.stop
        @change="emit('toggleMark', entry.id)"
      >
    </span>
    <span
      class="row__n"
      role="gridcell"
    >{{ entry.label }}</span>
    <span
      class="row__body"
      role="gridcell"
    >
      <span class="row__text">{{ rowText }}</span>
      <span class="row__meta">
        <template v-if="entry.kind === 'item' && entry.problem && entry.status !== 'converting'">
          {{ entry.typeLabel }} · <span class="xw-bad row__problem">{{ entry.problem }}</span>
        </template>
        <template v-else-if="entry.kind === 'item' && entry.status !== 'converting' && entry.points !== null">{{ entry.typeLabel }} · <span
          :class="{ 'xw-warn': pointsDiffer }"
          :data-test="pointsDiffer ? 'exam-workspace-row-points-differ' : undefined"
        >{{ examWorkspaceFormatPoints(entry.points) }} p</span></template>
        <template v-else>{{ meta }}</template>
      </span>
      <span
        v-if="entry.kind === 'parent'"
        class="row__pointsline"
        :data-test="childlessPart ? undefined : 'exam-workspace-part-points-line'"
        :aria-hidden="childlessPart ? 'true' : undefined"
      >
        <template v-if="!childlessPart">
          <span
            class="row__points"
            data-test="exam-workspace-part-points"
          >{{ examWorkspaceFormatPoints(entry.points) }} p</span>
        </template>
      </span>
    </span>
    <span role="gridcell"><span
      v-if="entry.kind === 'item' && entry.aiKey"
      class="xw-ai"
      :title="aiTitle"
      :aria-label="aiTitle"
      role="img"
    ><UiGlyph
      meaning="ai-assist"
      :size="16"
    /></span></span>
    <span role="gridcell"><span
      v-if="entry.kind === 'parent'"
    /><span
      v-else-if="entry.status === 'converting'"
      class="xw-muted"
      title="Konverteras"
      aria-label="Konverteras"
      role="img"
    ><UiGlyph
      meaning="busy"
      :size="16"
      class="xw-spin"
    /></span><span
      v-else-if="entry.status === 'ok'"
      class="xw-ok"
      title="Granskad"
      aria-label="Granskad"
      role="img"
    ><UiGlyph
      meaning="status-success"
      :size="16"
    /></span><span
      v-else
      class="xw-warn"
      title="Behöver granskas"
      aria-label="Behöver granskas"
      role="img"
    ><UiGlyph
      meaning="status-warning"
      :size="16"
    /></span></span>
  </div>
</template>

<style scoped>
.row {
  display: grid; grid-template-columns: 28px 28px minmax(0, 1fr) 20px 20px; align-items: center; gap: var(--huleedu-space-2);
  padding: var(--huleedu-space-2-5) var(--huleedu-space-4) var(--huleedu-space-2-5) var(--huleedu-space-6);
  border-bottom: 1px solid var(--huleedu-surface-divider); cursor: pointer; position: relative;
}
.row:focus-visible { outline: 2px solid var(--huleedu-action-40); outline-offset: -2px; }
.row--selected { background: var(--huleedu-action-10); box-shadow: inset 4px 0 0 var(--huleedu-action); }
.row__n { font-size: var(--huleedu-text-sm); color: var(--huleedu-navy-70); }
/* The mark cell keeps its grid track in both states; only its content is hidden when not marking. */
.row__mark { display: flex; align-items: center; }
.row__mark--idle { visibility: hidden; }
.row__body { min-width: 0; display: flex; flex-direction: column; }
.row__text {
  font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-medium);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.row__meta {
  font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.row__problem { font-weight: var(--huleedu-font-medium); }
/* The points line keeps its height with or without a printed difference, so no row moves. */
.row__pointsline {
  display: flex; flex-wrap: nowrap; align-items: center; gap: var(--huleedu-space-2);
  height: var(--xw-ctl-compact, 28px); min-width: 0;
}
.row__points {
  min-width: 0; font-size: var(--huleedu-text-xs); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: var(--huleedu-navy-60);
}
.row--parent .row__text { font-weight: var(--huleedu-font-normal); }
.row--child { padding-left: calc(var(--huleedu-space-6) + 24px); }
.row--child::before {
  content: ""; position: absolute; top: 0; bottom: 0; left: calc(var(--huleedu-space-6) + 8px);
  border-left: 2px solid var(--huleedu-navy-20);
}
.row--converting .row__text { color: var(--huleedu-navy-60); font-weight: var(--huleedu-font-normal); }
.row svg { display: block; }
@media (hover: hover) {
  .row:hover { background: var(--huleedu-action-05); }
  .row--selected:hover { background: var(--huleedu-action-10); }
}
@media (max-width: 1279px) {
  .row { padding-left: var(--huleedu-space-4); padding-right: var(--huleedu-space-3); }
  .row--child { padding-left: calc(var(--huleedu-space-4) + 20px); }
  .row--child::before { left: calc(var(--huleedu-space-4) + 6px); }
}
</style>
