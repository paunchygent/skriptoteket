<script setup lang="ts">
/**
 * Exam workspace Exportera drawer.
 *
 * Domain purpose:
 *   Export the saved exam with every choice in view: the format, and whether
 *   the file downloads or stays in Mina filer as the exam's one file of that
 *   format, replacing the earlier one. What stops the export comes first,
 *   with its fix, and disables the export until the last one is fixed; the
 *   export saves the exam first and runs from the version just saved (user
 *   rule 2026-10-17). After a QTI export the drawer lists what Exam.net
 *   loses on import, so the teacher can correct it there.
 *
 * Relationships:
 *   - Rendered inside `ExamWorkspaceDrawer` by `ExamWorkspaceView`; the
 *     exports run through `useExamWorkspaceExports`.
 */

import { computed, ref } from "vue";

import type {
  ExamWorkspaceExportChecklistEntry,
  ExamWorkspaceExportTarget,
} from "../../../api/examWorkspaceExports";
import { UiGlyph } from "../../../components/ui";
import ExamWorkspaceExportBlockers from "./ExamWorkspaceExportBlockers.vue";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import { EXAM_WORKSPACE_EXPORT_FORMATS, QTI_ZERO_POINTS_NOTE } from "./examWorkspaceExportFormats";
import { examWorkspaceQuestionLabel } from "./examWorkspaceRows";

type Destination = "download" | "files";

const props = defineProps<{
  blockers: ExamWorkspaceBlockerEntry[];
  busy: boolean;
  suggestBusy: boolean;
  exportingTarget: ExamWorkspaceExportTarget | null;
  /** When the exam's file of each format was saved in Mina filer this session. */
  savedExports: Partial<Record<ExamWorkspaceExportTarget, string>>;
  checklist: ExamWorkspaceExportChecklistEntry[];
  notice: string | null;
  /** What the last export made, e.g. "QTI-paketet är skapat." */
  result: string | null;
  /** Some question is worth 0 points, which Exam.net imports as 1. */
  zeroPoints: boolean;
}>();

const emit = defineEmits<{
  run: [target: ExamWorkspaceExportTarget, destination: Destination];
  goto: [blocker: ExamWorkspaceBlockerEntry];
  fix: [blocker: ExamWorkspaceBlockerEntry];
  suggestAll: [];
}>();

const target = ref<ExamWorkspaceExportTarget>("qti");
const destination = ref<Destination>("download");

const format = computed(() => EXAM_WORKSPACE_EXPORT_FORMATS.find((entry) => entry.target === target.value)!);
const replaced = computed(() => props.savedExports[target.value] ?? null);
const disabled = computed(() => props.blockers.length > 0 || props.busy || props.exportingTarget !== null);
</script>

<template>
  <ExamWorkspaceExportBlockers
    v-if="blockers.length > 0"
    :blockers="blockers"
    :fix-disabled="busy"
    :suggest-busy="suggestBusy"
    test-id="exam-workspace-export-drawer-blockers"
    @goto="emit('goto', $event)"
    @fix="emit('fix', $event)"
    @suggest-all="emit('suggestAll')"
  />

  <section class="sect">
    <h3>Format</h3>
    <div
      class="xw-seg xw-seg--large"
      role="group"
      aria-label="Format"
    >
      <button
        v-for="entry in EXAM_WORKSPACE_EXPORT_FORMATS"
        :key="entry.target"
        type="button"
        :aria-pressed="target === entry.target"
        :data-test="`exam-workspace-export-format-${entry.target}`"
        @click="target = entry.target"
      >
        {{ entry.name }}
      </button>
    </div>
    <p class="xw-hint">
      {{ format.hint }}
    </p>
    <p
      v-if="target === 'qti' && zeroPoints"
      class="xw-hint"
      data-test="exam-workspace-export-zero-points"
    >
      <UiGlyph
        meaning="info"
        :size="16"
      />{{ QTI_ZERO_POINTS_NOTE }}
    </p>
  </section>

  <section class="sect">
    <h3>Mål</h3>
    <label class="choice">
      <input
        v-model="destination"
        type="radio"
        name="exam-workspace-export-destination"
        value="download"
        data-test="exam-workspace-export-destination-download"
      >
      <span>Ladda ner</span>
    </label>
    <label class="choice">
      <input
        v-model="destination"
        type="radio"
        name="exam-workspace-export-destination"
        value="files"
        data-test="exam-workspace-export-destination-files"
      >
      <span>Spara i Mina filer<small>{{ replaced ? `Ersätter ${format.name}-filen från ${replaced}` : "Visas under provet i Mina filer" }}</small></span>
    </label>
  </section>

  <section class="sect">
    <button
      type="button"
      class="xw-btn xw-btn--primary"
      :disabled="disabled"
      data-test="exam-workspace-export-run"
      @click="emit('run', target, destination)"
    >
      <UiGlyph
        :meaning="exportingTarget ? 'busy' : destination === 'files' ? 'save-to-files' : 'download'"
        :size="20"
        :class="{ 'xw-spin': exportingTarget }"
      />{{ exportingTarget ? "Exporterar …" : destination === "files" ? "Spara i Mina filer" : "Ladda ner" }}
    </button>
    <p
      v-if="notice"
      class="xw-errline"
      role="status"
      data-test="exam-workspace-export-notice"
    >
      <UiGlyph
        meaning="status-warning"
        :size="16"
      />{{ notice }}
    </p>
    <p
      v-else-if="result"
      class="xw-okline"
      role="status"
      data-test="exam-workspace-export-result"
    >
      <UiGlyph
        meaning="status-success"
        :size="16"
      />{{ result }}
    </p>
  </section>

  <section
    v-if="checklist.length > 0"
    class="sect"
    data-test="exam-workspace-export-checklist"
  >
    <h3>
      <UiGlyph
        meaning="export-checklist"
        :size="16"
      />Det här tappar Exam.net vid import
    </h3>
    <ul class="checklist">
      <li
        v-for="(entry, index) in checklist"
        :key="index"
        class="xl"
      >
        <b :title="entry.question_text">{{ examWorkspaceQuestionLabel(Number(entry.question_number)) }}: {{ entry.question_text }}</b>
        <template v-if="entry.kind === 'free_text_criteria'">
          <span
            v-for="(criterion, criterionIndex) in entry.criteria"
            :key="criterionIndex"
          >{{ criterion.text }} ({{ criterion.points }} p)</span>
        </template>
        <span v-else-if="entry.kind === 'all_or_nothing'">Exam.net ger 1 poäng. Sätt {{ entry.points }} poäng.</span>
        <span v-else>Frågan ger {{ entry.points }} poäng. Varje lucka får {{ entry.gap_points }} poäng.</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.sect h3 {
  display: flex; align-items: center; gap: var(--huleedu-space-2); min-height: 28px; margin: 0 0 var(--huleedu-space-2-5);
  font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-semibold);
}
.choice { display: flex; align-items: flex-start; gap: var(--huleedu-space-3); padding: var(--huleedu-space-1-5) 0; font-size: var(--huleedu-text-sm); cursor: pointer; }
.choice small { display: block; color: var(--huleedu-navy-60); font-size: var(--huleedu-text-xs); }
.choice input { flex: none; width: 18px; height: 18px; margin: 2px 0 0; accent-color: var(--huleedu-action); }
.checklist { margin: 0; padding: 0; list-style: none; border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg); background: var(--huleedu-surface-content); }
.xl { display: grid; gap: 2px; padding: var(--huleedu-space-2-5) var(--huleedu-space-3); border-top: 1px solid var(--huleedu-surface-divider); font-size: var(--huleedu-text-sm); }
.xl:first-child { border-top: 0; }
.xl b { font-weight: var(--huleedu-font-semibold); }
.xl span { font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-70); }
</style>
