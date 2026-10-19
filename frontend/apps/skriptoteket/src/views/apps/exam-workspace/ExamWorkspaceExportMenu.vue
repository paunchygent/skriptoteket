<script setup lang="ts">
/**
 * Exam workspace Exportera button and menu.
 *
 * Domain purpose:
 *   Export the saved exam in one step: each format row is a labelled group
 *   with one outlined split button at its right edge, download first and
 *   save to Mina filer second (guests see the download part alone). A name
 *   click downloads, the same as the download part. A format click saves the
 *   exam first and exports the version just saved; the menu stays open and
 *   the running part spins while every part stays focusable but silent. What
 *   stops the export is listed first, with its fix, and disables the formats
 *   until the last one is fixed; the server's refusal stays the final check
 *   (user rule 2026-10-17). "Fler val …" opens the Exportera drawer.
 *
 * Relationships:
 *   - Rendered in the `export` slot of `ExamWorkspaceHeader`; the view runs
 *     the exports through `useExamWorkspaceExports` and passes the running
 *     destination down for the busy part.
 */

import { computed, ref } from "vue";

import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspaceExports";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceExportBlockers from "./ExamWorkspaceExportBlockers.vue";
import ExamWorkspaceMenu from "./ExamWorkspaceMenu.vue";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import {
  EXAM_WORKSPACE_EXPORT_FORMATS,
  QTI_ZERO_POINTS_NOTE,
  type ExamWorkspaceExportFormat,
} from "./examWorkspaceExportFormats";
import { useInjectedExamWorkspaceStore } from "./examWorkspaceStore";
import type { ExportDestination } from "./useExamWorkspaceExports";

const props = defineProps<{
  blockers: ExamWorkspaceBlockerEntry[];
  disabled: boolean;
  /** The exam is busy, so no blocker fix can run. */
  fixDisabled: boolean;
  suggestBusy: boolean;
  exportingTarget: ExamWorkspaceExportTarget | null;
  exportingDestination: ExportDestination | null;
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
  goto: [blocker: ExamWorkspaceBlockerEntry];
  fix: [blocker: ExamWorkspaceBlockerEntry];
  suggestAll: [];
}>();

const trigger = ref<HTMLButtonElement | null>(null);
const open = ref(false);
const store = useInjectedExamWorkspaceStore();
const isGuest = computed(() => store.teacher === null);
const formatsDisabled = computed(() => props.blockers.length > 0 || props.exportingTarget !== null);

function rowLabel(format: ExamWorkspaceExportFormat): string {
  return format.use === null ? format.name : `${format.name} ${format.use}`;
}

function isDownloadRunning(target: ExamWorkspaceExportTarget): boolean {
  return props.exportingTarget === target && props.exportingDestination === "download";
}

function isSaveRunning(target: ExamWorkspaceExportTarget): boolean {
  return props.exportingTarget === target && props.exportingDestination === "files";
}

function saveTitle(format: ExamWorkspaceExportFormat): string {
  const saved = props.savedExports[format.target];
  return saved === undefined
    ? `Spara ${format.name} i Mina filer`
    : `Spara ${format.name} i Mina filer (ersätter filen från ${saved})`;
}

function onDownload(target: ExamWorkspaceExportTarget): void {
  if (!formatsDisabled.value) {
    emit("download", target);
  }
}

function onSave(target: ExamWorkspaceExportTarget): void {
  if (!formatsDisabled.value) {
    emit("saveToFiles", target);
  }
}

function choose(action: () => void): void {
  open.value = false;
  action();
}
</script>

<template>
  <button
    ref="trigger"
    type="button"
    class="xw-cmd"
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
    <ExamWorkspaceExportBlockers
      v-if="blockers.length > 0"
      :blockers="blockers"
      :fix-disabled="fixDisabled"
      :suggest-busy="suggestBusy"
      test-id="exam-workspace-export-blockers"
      @goto="(blocker) => choose(() => emit('goto', blocker))"
      @fix="emit('fix', $event)"
      @suggest-all="emit('suggestAll')"
    />
    <div
      v-for="format in EXAM_WORKSPACE_EXPORT_FORMATS"
      :key="format.target"
      class="xw-mi"
      role="group"
      :aria-label="rowLabel(format)"
      :title="rowLabel(format)"
      :data-test="`exam-workspace-export-row-${format.target}`"
    >
      <span class="xw-mi__stack">
        <span
          class="xw-grow truncate"
          @click="onDownload(format.target)"
        >{{ format.name }} <span
          v-if="format.use !== null"
          class="xw-mi__sub"
        >{{ format.use }}</span></span>
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
      <span :class="{ 'xw-split': !isGuest }">
        <button
          type="button"
          class="xw-btn xw-btn--compact xw-btn--icon"
          role="menuitem"
          :aria-disabled="formatsDisabled || undefined"
          :aria-busy="isDownloadRunning(format.target) || undefined"
          :aria-label="`Ladda ner ${format.name}`"
          :title="`Ladda ner ${format.name}`"
          :data-test="`exam-workspace-export-${format.target}`"
          @click="onDownload(format.target)"
        >
          <UiGlyph
            :meaning="isDownloadRunning(format.target) ? 'busy' : 'download'"
            :size="16"
            :class="{ 'xw-spin': isDownloadRunning(format.target) }"
          />
        </button>
        <button
          v-if="!isGuest"
          type="button"
          class="xw-btn xw-btn--compact xw-btn--icon"
          role="menuitem"
          :aria-disabled="formatsDisabled || undefined"
          :aria-busy="isSaveRunning(format.target) || undefined"
          :aria-label="`Spara ${format.name} i Mina filer`"
          :title="saveTitle(format)"
          :data-test="`exam-workspace-export-save-${format.target}`"
          @click="onSave(format.target)"
        >
          <UiGlyph
            :meaning="isSaveRunning(format.target) ? 'busy' : 'save-to-files'"
            :size="16"
            :class="{ 'xw-spin': isSaveRunning(format.target) }"
          />
        </button>
      </span>
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
      <span class="xw-grow">Det här tappar Exam.net ({{ checklistCount }})</span>
    </button>
    <button
      type="button"
      class="xw-mi"
      role="menuitem"
      data-test="exam-workspace-export-more"
      @click="choose(() => emit('more'))"
    >
      <span class="xw-grow">Fler val …</span>
    </button>
  </ExamWorkspaceMenu>
</template>

<style scoped>
.xw-mi__stack .ex-note { display: block; white-space: normal; color: var(--huleedu-navy-70); }
@media (max-width: 1279px) {
  .ex-word { display: none; }
}
</style>
