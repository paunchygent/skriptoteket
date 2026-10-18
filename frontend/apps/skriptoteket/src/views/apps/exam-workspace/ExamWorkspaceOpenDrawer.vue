<script setup lang="ts">
/**
 * Exam workspace Öppna drawer.
 *
 * Domain purpose:
 *   Import an exam from Word (.docx) or DigiExam (.dxe), optionally for a
 *   course, and open a saved exam. While a conversion runs, its progress
 *   replaces the drop zone; finished questions can be edited at once. The
 *   saved exams group by course (the teacher's own courses first) or list
 *   newest first, and the teacher's choice is kept in the profile. The open
 *   exam is marked "Öppet" with its import notes and the files it saved in
 *   Mina filer this session. Import and opening wait while the open exam has
 *   unsaved changes.
 *
 * Relationships:
 *   - Rendered inside `ExamWorkspaceDrawer` by `ExamWorkspaceView`, which
 *     validates files and runs every emitted intent.
 */

import { computed, ref } from "vue";

import type { ExamListOrdering, ExamWorkspaceDocumentSummary } from "../../../api/examWorkspace";
import { UiGlyph } from "../../../components/ui";
import { AI_ADMIN_ONLY_NOTE, useAiAccess } from "../../../composables/useAiAccess";
import ExamCourseCombobox from "./ExamCourseCombobox.vue";
import { examWorkspaceOpenGroups } from "./examWorkspaceOpenGroups";
import { examWorkspaceDocumentLabel, examWorkspaceSavedAtLabel } from "./examWorkspaceRows";
import { examWorkspaceSameNameCounts } from "./examWorkspaceSavedDocuments";
import { useExamCourseCatalog } from "./useExamCourseCatalog";

const props = defineProps<{
  documents: ExamWorkspaceDocumentSummary[];
  currentLineageId: string | null;
  ordering: ExamListOrdering;
  /** No import now: busy, or the open exam has unsaved changes (one rule, also gating drops). */
  importBlocked: boolean;
  isBusy: boolean;
  isDirty: boolean;
  sourceFileError: string | null;
  conversionMessage: string | null;
  conversionError: string | null;
  conversionProgress: { done: number; total: number } | null;
  isConverting: boolean;
  notes: string[];
  /** The formats the open exam saved in Mina filer this session, e.g. "QTI". */
  currentExports: string[];
}>();

const emit = defineEmits<{
  selectFile: [file: File, courseKey: string | null];
  dropFiles: [files: File[], courseKey: string | null];
  open: [lineageId: string];
  setOrdering: [ordering: ExamListOrdering];
  retryConversion: [];
}>();

const { courses, courseByKey, registeredCourseKeys, error: courseCatalogError } = useExamCourseCatalog();
const { canUseAi } = useAiAccess();
const aiAdminOnlyNote = AI_ADMIN_ONLY_NOTE;
const courseKey = ref<string | null>(null);
const dragOver = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const groups = computed(() =>
  examWorkspaceOpenGroups(
    props.documents,
    props.ordering,
    registeredCourseKeys.value,
    (key) => courseByKey(key)?.name ?? null,
  ),
);
const sameName = computed(() => examWorkspaceSameNameCounts(props.documents));
const openBlocked = computed(() => props.isBusy || props.isDirty);

function handleFileInput(event: Event): void {
  const input = event.target as HTMLInputElement;
  const [file] = Array.from(input.files ?? []);
  if (file) {
    emit("selectFile", file, courseKey.value);
  }
  input.value = "";
}

function handleDrop(event: DragEvent): void {
  dragOver.value = false;
  emit("dropFiles", Array.from(event.dataTransfer?.files ?? []), courseKey.value);
}

function openEntry(entry: ExamWorkspaceDocumentSummary): void {
  if (entry.lineage_id !== props.currentLineageId && !openBlocked.value) {
    emit("open", entry.lineage_id);
  }
}
</script>

<template>
  <section
    class="sect"
    data-test="exam-workspace-files-source"
  >
    <h3>Importera prov</h3>
    <label
      class="xw-label sect__first"
      for="exam-workspace-import-course"
    >Kurs (valfritt)</label>
    <ExamCourseCombobox
      v-model="courseKey"
      input-id="exam-workspace-import-course"
      :courses="courses"
      :disabled="importBlocked"
    />
    <p
      v-if="courseCatalogError"
      class="xw-errline"
      role="status"
    >
      {{ courseCatalogError }}
    </p>
    <div
      v-if="conversionMessage"
      class="prog"
      role="status"
      aria-live="polite"
      data-test="exam-workspace-conversion-status"
    >
      <div class="prog__line">
        <UiGlyph
          v-if="isConverting"
          meaning="busy"
          :size="16"
          class="xw-spin"
        /><span>{{ conversionMessage }}</span>
      </div>
      <div
        v-if="conversionProgress"
        class="prog__bar"
        role="progressbar"
        aria-label="Konverterade frågor"
        aria-valuemin="0"
        :aria-valuemax="conversionProgress.total"
        :aria-valuenow="conversionProgress.done"
        data-test="exam-workspace-conversion-progress"
      >
        <i :style="{ width: `${(100 * conversionProgress.done) / conversionProgress.total}%` }" />
      </div>
      <small
        v-if="conversionProgress && conversionProgress.done > 0"
        class="xw-muted"
      >Klara frågor går att redigera direkt.</small>
      <button
        v-if="isConverting && conversionError"
        type="button"
        class="xw-btn xw-btn--compact prog__retry"
        data-test="exam-workspace-conversion-retry"
        @click="emit('retryConversion')"
      >
        <UiGlyph
          meaning="retry"
          :size="16"
        />Försök igen
      </button>
      <small
        v-else-if="!isConverting"
        class="xw-muted"
      >Välj provfilen igen för att försöka på nytt.</small>
    </div>
    <div
      v-if="!isConverting"
      class="drop"
      :class="{ 'drop--over': dragOver && !importBlocked, 'drop--off': importBlocked }"
      data-test="exam-workspace-drop-zone"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop.prevent="handleDrop"
    >
      <UiGlyph
        meaning="upload"
        :size="32"
        class="drop__glyph"
      />
      <b class="drop__title">Provfil</b>
      <span class="drop__formats">
        <span
          v-if="canUseAi"
          class="xw-chip"
        >Word .docx</span>
        <span class="xw-chip">DigiExam .dxe</span>
      </span>
      <input
        ref="fileInput"
        class="drop__input"
        type="file"
        :accept="canUseAi ? '.docx,.dxe' : '.dxe'"
        :disabled="importBlocked"
        tabindex="-1"
        aria-hidden="true"
        data-test="exam-workspace-source-file-input"
        @change="handleFileInput"
      >
      <button
        type="button"
        class="xw-btn"
        :disabled="importBlocked"
        data-test="exam-workspace-pick-file"
        @click="fileInput?.click()"
      >
        <UiGlyph
          meaning="upload"
          :size="20"
        />Välj provfil
      </button>
      <small>eller dra hit filen</small>
      <small
        v-if="!canUseAi"
        class="xw-muted"
      >{{ aiAdminOnlyNote }}</small>
    </div>
    <p
      v-if="sourceFileError"
      class="xw-errline"
      data-test="exam-workspace-source-file-error"
    >
      <UiGlyph
        meaning="blocker"
        :size="16"
      />{{ sourceFileError }}
    </p>
    <p
      v-else-if="isDirty"
      class="xw-hint"
      data-test="exam-workspace-open-dirty-hint"
    >
      <UiGlyph
        meaning="info"
        :size="16"
      />Spara det öppna provet innan du importerar eller öppnar ett annat.
    </p>
  </section>

  <section
    class="sect"
    data-test="exam-workspace-saved-documents"
  >
    <h3>
      <span class="xw-grow">Prov</span>
      <span
        class="xw-seg"
        role="group"
        aria-label="Ordning"
      >
        <button
          type="button"
          :aria-pressed="ordering === 'course'"
          data-test="exam-workspace-ordering-course"
          @click="ordering !== 'course' && emit('setOrdering', 'course')"
        >Per kurs</button>
        <button
          type="button"
          :aria-pressed="ordering === 'newest'"
          data-test="exam-workspace-ordering-newest"
          @click="ordering !== 'newest' && emit('setOrdering', 'newest')"
        >Senaste</button>
      </span>
    </h3>
    <p
      v-if="groups.length === 0"
      class="xw-hint"
    >
      Inga sparade prov ännu.
    </p>
    <div
      v-for="group in groups"
      :key="group.courseKey ?? group.heading ?? 'all'"
      class="egroup"
    >
      <h4 v-if="group.heading">
        {{ group.heading }}<span
          v-if="group.courseKey"
          class="egroup__code"
        >{{ group.courseKey }}</span>
      </h4>
      <div class="files">
        <div
          v-for="entry in group.documents"
          :key="entry.lineage_id"
          class="file"
          :class="{ 'file--current': entry.lineage_id === currentLineageId }"
          role="button"
          tabindex="0"
          :aria-disabled="(entry.lineage_id !== currentLineageId && openBlocked) || undefined"
          :aria-current="entry.lineage_id === currentLineageId || undefined"
          :title="entry.lineage_id !== currentLineageId && isDirty ? 'Spara det öppna provet innan du öppnar ett annat.' : undefined"
          :data-test="`exam-workspace-open-${entry.lineage_id}`"
          @click="openEntry(entry)"
          @keydown.enter.prevent="openEntry(entry)"
          @keydown.space.prevent="openEntry(entry)"
        >
          <UiGlyph
            meaning="document"
            :size="16"
          />
          <span class="file__body">
            <span class="file__title">{{ entry.title || examWorkspaceDocumentLabel(entry.name) }}</span>
            <span class="file__meta">
              <span>{{ examWorkspaceDocumentLabel(entry.name) }}</span>
              <span>Sparad {{ examWorkspaceSavedAtLabel(entry.saved_at) }}</span>
              <span v-if="sameName[entry.lineage_id]">{{ sameName[entry.lineage_id] }}</span>
              <template v-if="entry.lineage_id === currentLineageId">
                <span
                  v-for="format in currentExports"
                  :key="format"
                  class="xw-chip"
                  :title="`${format} i Mina filer`"
                ><UiGlyph
                  meaning="save-to-files"
                  :size="12"
                />{{ format }}</span>
              </template>
            </span>
            <ul
              v-if="entry.lineage_id === currentLineageId && notes.length > 0"
              class="file__notes"
              data-test="exam-workspace-notes"
            >
              <li
                v-for="note in notes"
                :key="note"
              >
                <UiGlyph
                  meaning="info"
                  :size="14"
                /><span>{{ note }}</span>
              </li>
            </ul>
          </span>
          <span
            v-if="entry.lineage_id === currentLineageId"
            class="file__tag"
          >Öppet</span>
          <span v-else />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.sect h3 {
  display: flex; align-items: center; gap: var(--huleedu-space-2); min-height: 28px; margin: 0 0 var(--huleedu-space-2-5);
  font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-semibold);
}
.sect .sect__first { margin-top: 0; }
.sect > * + .prog, .sect > * + .drop { margin-top: var(--huleedu-space-3); }
.drop {
  display: flex; flex-direction: column; align-items: center; gap: var(--huleedu-space-2); padding: var(--huleedu-space-5);
  border: 1px dashed var(--huleedu-navy-30); border-radius: var(--huleedu-radius-lg); background: var(--huleedu-surface-content);
  text-align: center;
}
.drop--over { border-color: var(--huleedu-action); background: var(--huleedu-action-05); }
.drop--off { opacity: 0.55; }
.drop__glyph { color: var(--huleedu-navy-40); }
.drop__title { font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-semibold); }
.drop__formats { display: flex; gap: var(--huleedu-space-2); }
.drop__input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.drop small { color: var(--huleedu-navy-60); font-size: var(--huleedu-text-xs); }
.prog {
  display: grid; gap: var(--huleedu-space-2); padding: var(--huleedu-space-3) var(--huleedu-space-4);
  border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg); background: var(--huleedu-surface-content);
  font-size: var(--huleedu-text-sm);
}
.prog__line { display: flex; align-items: center; gap: var(--huleedu-space-2); }
.prog__bar { height: 6px; overflow: hidden; border-radius: 3px; border: 1px solid var(--huleedu-surface-divider); background: var(--huleedu-navy-02); }
.prog__bar > i { display: block; height: 100%; background: var(--huleedu-action); }
.prog small { font-size: var(--huleedu-text-xs); }
.prog__retry { justify-self: start; }
.egroup + .egroup { margin-top: var(--huleedu-space-4); }
.egroup h4 {
  display: flex; gap: var(--huleedu-space-2); margin: 0 0 var(--huleedu-space-1-5);
  font-size: var(--huleedu-text-xs); font-weight: var(--huleedu-font-semibold); color: var(--huleedu-navy-70);
}
.egroup__code { font-family: var(--huleedu-font-mono); font-weight: var(--huleedu-font-normal); color: var(--huleedu-navy-60); }
.files { overflow: hidden; border: 1px solid var(--huleedu-panel-border); border-radius: var(--huleedu-radius-lg); background: var(--huleedu-surface-content); }
.file {
  display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; align-items: start; gap: var(--huleedu-space-3);
  padding: var(--huleedu-space-2-5) var(--huleedu-space-3); border-top: 1px solid var(--huleedu-surface-divider); cursor: pointer;
}
.file:first-child { border-top: 0; }
.file:focus-visible { outline: 2px solid var(--huleedu-action-40); outline-offset: -2px; }
.file > svg { margin-top: 2px; color: var(--huleedu-navy-60); }
.file--current { background: var(--huleedu-action-05); box-shadow: inset 3px 0 0 var(--huleedu-action); cursor: default; }
.file[aria-disabled="true"] { cursor: not-allowed; }
.file[aria-disabled="true"] .file__title { color: var(--huleedu-navy-50); }
.file__body { min-width: 0; }
.file__title { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--huleedu-text-sm); font-weight: var(--huleedu-font-medium); }
.file__meta {
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--huleedu-space-1-5); margin-top: 3px;
  font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-60);
}
.file__notes { display: grid; gap: 2px; margin: var(--huleedu-space-1-5) 0 0; padding: 0; list-style: none; font-size: var(--huleedu-text-xs); color: var(--huleedu-navy-70); }
.file__notes li { display: flex; gap: var(--huleedu-space-1-5); }
.file__tag { font-size: var(--huleedu-text-xs); font-weight: var(--huleedu-font-semibold); color: var(--huleedu-action); }
@media (hover: hover) { .file:not([aria-disabled="true"]):not(.file--current):hover { background: var(--huleedu-action-05); } }
</style>
