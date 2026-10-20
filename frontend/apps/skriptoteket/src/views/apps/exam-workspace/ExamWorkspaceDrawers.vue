<script setup lang="ts">
/**
 * The exam workspace's one open drawer (TASK-SKRIPT-40-04-03).
 *
 * Domain purpose:
 *   Show the drawer the teacher opened: Öppna (saved exams and Import),
 *   Exportera (the export blockers, formats and checklist) or Provets
 *   uppgifter (title, course, tags and content suggestions).
 *
 * Relationships:
 *   - Reads the exam from the `editing` composable result and the export,
 *     source-file and content state from theirs; commands that need the
 *     view's save flow or selection leave as events.
 *   - Rendered by `ExamWorkspaceView` while a drawer is open.
 */

import { computed } from "vue";

import type { ExamListOrdering } from "../../../api/examWorkspace";
import type { ExamWorkspaceExportTarget } from "../../../api/examWorkspaceExports";
import type { ExamWorkspaceBlockerEntry } from "./examWorkspaceBlockers";
import ExamWorkspaceDetailsDrawer from "./ExamWorkspaceDetailsDrawer.vue";
import ExamWorkspaceDrawer from "./ExamWorkspaceDrawer.vue";
import ExamWorkspaceExportDrawer from "./ExamWorkspaceExportDrawer.vue";
import ExamWorkspaceOpenDrawer from "./ExamWorkspaceOpenDrawer.vue";
import { EXAM_WORKSPACE_EXPORT_FORMATS } from "./examWorkspaceExportFormats";
import type { useExamWorkspaceContentSuggestions } from "./useExamWorkspaceContentSuggestions";
import type { useExamWorkspaceEditing } from "./useExamWorkspaceEditing";
import type { useExamWorkspaceEnrichment } from "./useExamWorkspaceEnrichment";
import type { useExamWorkspaceExports } from "./useExamWorkspaceExports";
import type { ExamWorkspaceLayout } from "./useExamWorkspaceLayout";
import type { useExamWorkspaceSourceFile } from "./useExamWorkspaceSourceFile";

type DrawerName = "open" | "export" | "details";

const DRAWER_TITLES: Record<DrawerName, string> = {
  details: "Provets uppgifter",
  export: "Exportera",
  open: "Öppna",
};
const DRAWER_OPENERS: Record<DrawerName, string> = {
  details: '[data-test="exam-workspace-details"]',
  export: '[data-test="exam-workspace-export"]',
  open: '[data-test="exam-workspace-open"]',
};

const props = withDefaults(
  defineProps<{
    drawer: DrawerName;
    layout: ExamWorkspaceLayout;
    editing: ReturnType<typeof useExamWorkspaceEditing>;
    exports: ReturnType<typeof useExamWorkspaceExports>;
    enrichment: ReturnType<typeof useExamWorkspaceEnrichment>;
    content: ReturnType<typeof useExamWorkspaceContentSuggestions>;
    sourceFile: ReturnType<typeof useExamWorkspaceSourceFile>;
    blockers: ExamWorkspaceBlockerEntry[];
    disabled: boolean;
    enrichmentBusy: boolean;
    zeroPoints: boolean;
    formattedSavedExports: Partial<Record<ExamWorkspaceExportTarget, string>>;
    questionLabel: (itemId: string) => string | null;
    /** The desktop resize handle is wanted; only ever set on desktop. */
    handle?: boolean;
    /** Importera in the header asked for the file picker; the Öppna drawer acts on it and reports back. */
    importPickPending?: boolean;
  }>(),
  { handle: false, importPickPending: false },
);

defineEmits<{
  close: [];
  "import-pick-consumed": [];
  run: [target: ExamWorkspaceExportTarget, destination: "download" | "files"];
  goto: [blocker: ExamWorkspaceBlockerEntry];
  fix: [blocker: ExamWorkspaceBlockerEntry];
  "set-ordering": [ordering: ExamListOrdering];
  /** The resize handle reports a dragged or stepped width in px. */
  set: [px: number];
  /** The resize handle resets to the default width on double-click. */
  reset: [];
  /** Enter on the resize handle; the view closes the drawer like its ×. */
  "toggle-collapse": [];
}>();

const {
  conversionError,
  conversionMessage,
  conversionProgress,
  importBlocked,
  isBusy,
  isConverting,
  isDirty,
  listOrdering,
  notes,
  openDocument,
  renameFailure,
  renameFile,
  retryConversionStatus,
  savedDocuments,
  setCourse,
  setTags,
  setTitle,
  summary,
  workspaceDocument,
} = props.editing;
const { handleDroppedFiles, handleSelectedFile, sourceFileError } = props.sourceFile;

const currentExports = computed(() =>
  EXAM_WORKSPACE_EXPORT_FORMATS.filter(
    (format) => props.exports.savedExports.value[format.target] !== undefined,
  ).map((format) => format.name),
);
/** The one save status for the Öppna drawer: its state and, while unsaved, its own reason. */
const openSaveStatus = computed(() => props.editing.history.saveStatus.value);
const openSaveState = computed(() => openSaveStatus.value.state);
const openSaveDetail = computed(() =>
  openSaveStatus.value.state === "unsaved" ? openSaveStatus.value.detail : null,
);
</script>

<template>
  <ExamWorkspaceDrawer
    :key="drawer"
    :title="DRAWER_TITLES[drawer]"
    :layout="layout"
    :opener-selector="DRAWER_OPENERS[drawer]"
    :test-id="`exam-workspace-drawer-${drawer}`"
    :handle="handle"
    @close="$emit('close')"
    @set="$emit('set', $event)"
    @reset="$emit('reset')"
    @toggle-collapse="$emit('toggle-collapse')"
  >
    <ExamWorkspaceOpenDrawer
      v-if="drawer === 'open'"
      :documents="savedDocuments"
      :current-lineage-id="summary?.lineage_id ?? null"
      :ordering="listOrdering"
      :import-blocked="importBlocked"
      :is-busy="isBusy"
      :is-dirty="isDirty"
      :save-state="openSaveState"
      :save-detail="openSaveDetail"
      :source-file-error="sourceFileError"
      :conversion-message="conversionMessage"
      :conversion-error="conversionError"
      :conversion-progress="conversionProgress"
      :is-converting="isConverting"
      :notes="notes"
      :current-exports="currentExports"
      :import-pick-pending="importPickPending"
      @select-file="handleSelectedFile"
      @drop-files="handleDroppedFiles"
      @open="openDocument"
      @set-ordering="$emit('set-ordering', $event)"
      @retry-conversion="retryConversionStatus"
      @import-pick-consumed="$emit('import-pick-consumed')"
    />
    <ExamWorkspaceExportDrawer
      v-else-if="drawer === 'export' && workspaceDocument"
      :blockers="blockers"
      :busy="disabled"
      :suggest-busy="enrichmentBusy"
      :exporting-target="exports.exportingTarget.value"
      :saved-exports="formattedSavedExports"
      :checklist="exports.exportChecklist.value"
      :notice="exports.exportNotice.value"
      :result="exports.exportResult.value"
      :zero-points="zeroPoints"
      :question-label="questionLabel"
      @run="(target, destination) => $emit('run', target, destination)"
      @goto="$emit('goto', $event)"
      @fix="$emit('fix', $event)"
      @suggest-all="enrichment.requestSuggestionsForAll"
    />
    <ExamWorkspaceDetailsDrawer
      v-else-if="drawer === 'details' && workspaceDocument && summary"
      :document="workspaceDocument"
      :summary="summary"
      :rename-file="renameFile"
      :rename-failure="renameFailure"
      :disabled="disabled"
      :dirty="isDirty"
      :content-busy="content.busy.value"
      :content-message="content.message.value"
      :question-label="questionLabel"
      @update:title="setTitle"
      @update:course="setCourse"
      @set-tags="setTags"
      @suggest-content="content.suggest"
    />
  </ExamWorkspaceDrawer>
</template>
