<script setup lang="ts">
/**
 * Exam workspace Exportera button and menu.
 *
 * Domain purpose:
 *   Export the saved exam in one step: each format row downloads the file
 *   and its folder button keeps it in Mina filer instead, replacing the
 *   exam's earlier file of that format. The questions to fix are listed
 *   first and lead to the question. The server decides what stops an
 *   export: what the workspace itself sees is guidance, so only the
 *   server's refusal, unsaved changes (exports are made from the saved exam)
 *   or a running export disable the formats. "Fler val …" opens the
 *   Exportera drawer.
 *
 * Relationships:
 *   - Rendered in the `export` slot of `ExamWorkspaceHeader`; the view runs
 *     the exports through `useExamWorkspaceExports`.
 */

import { computed, ref } from "vue";

import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import { EXAM_WORKSPACE_EXPORT_FORMATS, QTI_ZERO_POINTS_NOTE } from "./examWorkspaceExportFormats";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceListEntries";

const props = defineProps<{
  blockers: ExamWorkspaceBlockerEntry[];
  /** The server refused the last export for these questions. */
  serverBlocked: boolean;
  disabled: boolean;
  dirty: boolean;
  exportingTarget: ExamWorkspaceExportTarget | null;
  savedExports: Partial<Record<ExamWorkspaceExportTarget, string>>;
  /** What the last export made, e.g. "QTI-paketet är skapat." */
  result: string | null;
  /** What Exam.net loses after the last QTI export; opens Exportera with the list. */
  checklistCount: number;
  /** Some question is worth 0 points, which Exam.net imports as 1. */
  zeroPoints: boolean;
  isPhone: boolean;
}>();

const emit = defineEmits<{
  download: [target: ExamWorkspaceExportTarget];
  saveToFiles: [target: ExamWorkspaceExportTarget];
  more: [];
  goto: [itemId: string];
}>();

const trigger = ref<HTMLButtonElement | null>(null);
const open = ref(false);
const formatsDisabled = computed(
  () => props.serverBlocked || props.dirty || props.exportingTarget !== null,
);

function choose(action: () => void): void {
  open.value = false;
  action();
}
</script>

<template>
  <button
    ref="trigger"
    type="button"
    class="xw-btn ex-trigger"
    :disabled="disabled"
    aria-haspopup="menu"
    :aria-expanded="open"
    aria-label="Exportera"
    title="Exportera provet"
    data-test="exam-workspace-export"
    @click="open = !open"
  >
    <UiGlyph
      :meaning="exportingTarget ? 'busy' : 'download'"
      :size="20"
      :class="{ 'xw-spin': exportingTarget }"
    /><span class="ex-word">Exportera</span><UiGlyph
      class="ex-word"
      meaning="open-list"
      :size="16"
    />
  </button>
  <ExamWorkspaceMenu
    :open="open"
    :anchor="trigger"
    :align="isPhone ? 'left' : 'right'"
    label="Exportera"
    test-id="exam-workspace-export-menu"
    @close="open = false"
  >
    <div
      v-if="blockers.length > 0"
      class="xw-mblock"
      :class="{ 'xw-mblock--warn': !serverBlocked }"
      data-test="exam-workspace-export-blockers"
    >
      <b><UiGlyph
        :meaning="serverBlocked ? 'status-failure' : 'status-warning'"
        :size="16"
      />{{ serverBlocked ? "Kan inte exporteras ännu" : "Kontrollera innan du exporterar" }}</b>
      <button
        v-for="blocker in blockers"
        :key="`${blocker.itemId}-${blocker.reason}`"
        type="button"
        @click="choose(() => emit('goto', blocker.itemId))"
      >
        Fråga {{ blocker.label }}: {{ blocker.reason }}
      </button>
    </div>
    <p
      v-else-if="dirty"
      class="xw-mhead"
    >
      Spara provet först. Exporten görs från det sparade provet.
    </p>
    <div
      v-for="format in EXAM_WORKSPACE_EXPORT_FORMATS"
      :key="format.target"
      class="xw-mi"
      role="menuitem"
      :tabindex="formatsDisabled ? -1 : 0"
      :aria-disabled="formatsDisabled || undefined"
      :title="`Ladda ner ${format.name}`"
      :data-test="`exam-workspace-export-${format.target}`"
      @click="!formatsDisabled && choose(() => emit('download', format.target))"
      @keydown.enter.self.prevent="!formatsDisabled && choose(() => emit('download', format.target))"
      @keydown.space.self.prevent="!formatsDisabled && choose(() => emit('download', format.target))"
    >
      <UiGlyph
        meaning="download"
        :size="20"
      />
      <span class="xw-mi__stack">
        <span class="xw-grow">{{ format.name }} <span class="xw-mi__sub">{{ format.use }}</span></span>
        <small v-if="savedExports[format.target]"><UiGlyph
          meaning="save-to-files"
          :size="14"
        />I Mina filer {{ savedExports[format.target] }}</small>
        <small
          v-if="format.target === 'qti' && zeroPoints"
          class="ex-note"
          data-test="exam-workspace-export-zero-points"
        >{{ QTI_ZERO_POINTS_NOTE }}</small>
      </span>
      <button
        type="button"
        class="xw-mi__mini"
        :disabled="formatsDisabled"
        :title="savedExports[format.target]
          ? `Spara ${format.name} i Mina filer (ersätter filen från ${savedExports[format.target]})`
          : `Spara ${format.name} i Mina filer`"
        :aria-label="`Spara ${format.name} i Mina filer`"
        :data-test="`exam-workspace-export-save-${format.target}`"
        @click.stop="choose(() => emit('saveToFiles', format.target))"
      >
        <UiGlyph
          meaning="save-to-files"
          :size="20"
        />
      </button>
    </div>
    <div class="xw-mdiv" />
    <p
      v-if="result"
      class="xw-mhead xw-ok"
      role="status"
      data-test="exam-workspace-export-menu-result"
    >
      {{ result }}
    </p>
    <button
      v-if="checklistCount > 0"
      type="button"
      class="xw-mi"
      role="menuitem"
      data-test="exam-workspace-export-checklist-open"
      @click="choose(() => emit('more'))"
    >
      <UiGlyph
        meaning="export-checklist"
        :size="20"
      /><span class="xw-grow">Det här tappar Exam.net ({{ checklistCount }})</span>
    </button>
    <button
      type="button"
      class="xw-mi"
      role="menuitem"
      data-test="exam-workspace-export-more"
      @click="choose(() => emit('more'))"
    >
      <span class="xw-mi__pad" /><span class="xw-grow">Fler val …</span>
    </button>
  </ExamWorkspaceMenu>
</template>

<style scoped>
.xw-mi__stack .ex-note { display: block; white-space: normal; color: var(--huleedu-navy-70); }
@media (max-width: 1279px) {
  .ex-word { display: none; }
  .ex-trigger { width: var(--xw-ctl-fine, 36px); padding: 0; }
}
@media (max-width: 1279px) and (pointer: coarse) {
  .ex-trigger { width: var(--xw-ctl, 44px); }
}
@media (max-width: 767px) {
  .ex-trigger { width: var(--xw-ctl, 44px); }
}
</style>
