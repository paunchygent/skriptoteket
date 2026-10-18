<script setup lang="ts">
/**
 * Exam workspace question list row.
 *
 * Domain purpose:
 *   One entry of the question list: its number, the start of its text and
 *   one line naming its type and points, or the first thing that stops its
 *   export in red. A question shows whether the AI wrote its key and whether
 *   it is reviewed, needs review or still converts. An instruction row shows
 *   how many deluppgifter it holds and their points; when the exam text
 *   prints another part total, the points line says so in amber and wraps
 *   instead of truncating. Its deluppgifter are indented under it.
 *
 * Relationships:
 *   - Rendered by `ExamWorkspaceQuestionList`; receives `selected` as a
 *     boolean, so moving the selection re-renders only the two rows involved.
 */

import { computed } from "vue";

import { UiGlyph } from "../../../components/ui";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { examWorkspaceFormatPoints, examWorkspacePointsLine } from "./examWorkspaceTotals";

const props = defineProps<{
  entry: ExamWorkspaceListEntry;
  selected: boolean;
  disabled: boolean;
}>();

const emit = defineEmits<{ select: [id: string]; acceptTotal: [parentId: string] }>();

const meta = computed(() => {
  const entry = props.entry;
  if (entry.kind === "parent") {
    const count = entry.childIds.length;
    const questions = `Instruktion · ${count} ${count === 1 ? "fråga" : "frågor"}`;
    return entry.printedTotal === null ? `${questions} · ${examWorkspaceFormatPoints(entry.points)} p` : questions;
  }
  if (entry.status === "converting") {
    return "Konverteras …";
  }
  return entry.points === null ? entry.typeLabel : `${entry.typeLabel} · ${examWorkspaceFormatPoints(entry.points)} p`;
});

const aiTitle = computed(() =>
  props.entry.kind === "item" && props.entry.aiKey === "interpreted" ? "Tolkad av AI" : "Förslag från AI",
);
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
    role="option"
    :aria-selected="selected"
    :tabindex="selected ? 0 : -1"
    :data-entry-id="entry.id"
    :data-test="`exam-workspace-row-${entry.id}`"
    @click="emit('select', entry.id)"
  >
    <span class="row__n">{{ entry.label }}</span>
    <span class="row__body">
      <span class="row__text">{{ entry.text || "Ny fråga" }}</span>
      <span class="row__meta">
        <template v-if="entry.kind === 'item' && entry.problem && entry.status !== 'converting'">
          {{ entry.typeLabel }} · <span class="xw-bad row__problem">{{ entry.problem }}</span>
        </template>
        <template v-else>{{ meta }}</template>
      </span>
      <span
        v-if="entry.kind === 'parent' && entry.printedTotal !== null"
        class="row__printedline"
      >
        <span
          class="row__printed"
          data-test="exam-workspace-part-points"
        >{{ examWorkspacePointsLine(entry.points, entry.printedTotal) }}</span>
        <button
          type="button"
          class="xw-btn xw-btn--compact xw-btn--ghost"
          :disabled="disabled"
          :data-test="`exam-workspace-accept-part-total-${entry.id}`"
          @click.stop="emit('acceptTotal', entry.id)"
        >
          Använd {{ examWorkspaceFormatPoints(entry.points) }} p
        </button>
      </span>
    </span>
    <span
      v-if="entry.kind === 'item' && entry.aiKey"
      class="xw-ai"
      :title="aiTitle"
      :aria-label="aiTitle"
      role="img"
    ><UiGlyph
      meaning="ai-assist"
      :size="16"
    /></span>
    <span v-else />
    <span v-if="entry.kind === 'parent'" />
    <span
      v-else-if="entry.status === 'converting'"
      class="xw-muted"
      title="Konverteras"
      aria-label="Konverteras"
      role="img"
    ><UiGlyph
      meaning="busy"
      :size="16"
      class="xw-spin"
    /></span>
    <span
      v-else-if="entry.status === 'ok'"
      class="xw-ok"
      title="Granskad"
      aria-label="Granskad"
      role="img"
    ><UiGlyph
      meaning="status-success"
      :size="16"
    /></span>
    <span
      v-else
      class="xw-warn"
      title="Behöver granskas"
      aria-label="Behöver granskas"
      role="img"
    ><UiGlyph
      meaning="status-warning"
      :size="16"
    /></span>
  </div>
</template>

<style scoped>
.row {
  display: grid; grid-template-columns: 28px minmax(0, 1fr) 20px 20px; align-items: center; gap: var(--huleedu-space-2);
  padding: var(--huleedu-space-2-5) var(--huleedu-space-4) var(--huleedu-space-2-5) var(--huleedu-space-6);
  border-bottom: 1px solid var(--huleedu-surface-divider); cursor: pointer; position: relative;
}
.row:focus-visible { outline: 2px solid var(--huleedu-action-40); outline-offset: -2px; }
.row--selected { background: var(--huleedu-action-10); box-shadow: inset 4px 0 0 var(--huleedu-action); }
.row__n { font-size: var(--huleedu-text-sm); color: var(--huleedu-navy-70); }
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
.row__printedline { display: flex; flex-wrap: wrap; align-items: center; gap: 0 var(--huleedu-space-2); }
.row__printed { font-size: var(--huleedu-text-xs); color: var(--huleedu-warning); overflow-wrap: anywhere; }
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
