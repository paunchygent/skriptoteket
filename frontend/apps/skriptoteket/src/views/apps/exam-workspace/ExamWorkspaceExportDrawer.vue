<script setup lang="ts">
/**
 * Exam workspace Exportera drawer.
 *
 * Domain purpose:
 *   Export the saved exam with every choice in view: the format, and whether
 *   the file downloads or stays in Mina filer as the exam's one file of that
 *   format, replacing the earlier one. The questions to fix come first and
 *   lead to the question; only the server's refusal stops the export, what
 *   the workspace itself sees is guidance. After a QTI export the drawer lists what
 *   Exam.net loses on import, so the teacher can correct it there.
 *
 * Relationships:
 *   - Rendered inside `ExamWorkspaceDrawer` by `ExamWorkspaceView`; the
 *     exports run through `useExamWorkspaceExports`.
 */

import { computed, ref } from "vue";

import type {
  ExamWorkspaceExportChecklistEntry,
  ExamWorkspaceExportTarget,
} from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { EXAM_WORKSPACE_EXPORT_FORMATS, QTI_ZERO_POINTS_NOTE } from "./examWorkspaceExportFormats";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceListEntries";
import { examWorkspaceQuestionLabel } from "./examWorkspaceRows";

type Destination = "download" | "files";

const props = defineProps<{
  blockers: ExamWorkspaceBlockerEntry[];
  /** The server refused the last export for these questions. */
  serverBlocked: boolean;
  dirty: boolean;
  busy: boolean;
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
  goto: [itemId: string];
}>();

const target = ref<ExamWorkspaceExportTarget>("qti");
const destination = ref<Destination>("download");

const format = computed(() => EXAM_WORKSPACE_EXPORT_FORMATS.find((entry) => entry.target === target.value)!);
const replaced = computed(() => props.savedExports[target.value] ?? null);
const disabled = computed(
  () => props.serverBlocked || props.dirty || props.busy || props.exportingTarget !== null,
);
</script>

<template>
  <div
    v-if="blockers.length > 0"
    class="xw-mblock"
    :class="{ 'xw-mblock--warn': !serverBlocked }"
    data-test="exam-workspace-export-drawer-blockers"
  >
    <b><UiGlyph
      :meaning="serverBlocked ? 'status-failure' : 'status-warning'"
      :size="16"
    />{{ serverBlocked ? "Kan inte exporteras ännu" : "Kontrollera innan du exporterar" }}</b>
    <button
      v-for="blocker in blockers"
      :key="`${blocker.itemId}-${blocker.reason}`"
      type="button"
      :data-test="`exam-workspace-blocker-${blocker.itemId}`"
      @click="emit('goto', blocker.itemId)"
    >
      Fråga {{ blocker.label }}: {{ blocker.reason }}
    </button>
  </div>

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
      />{{ destination === "files" ? "Spara i Mina filer" : "Ladda ner" }}
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
    <p
      v-else-if="dirty"
      class="xw-hint"
    >
      <UiGlyph
        meaning="info"
        :size="16"
      />Spara provet innan du skapar filer. Filerna skapas från den sparade versionen.
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
