<script setup lang="ts">
/**
 * Grouping workspace pane.
 *
 * This component composes the grouping-only student pool, action row, and
 * group board. It keeps the task-specific grouping chrome outside the global
 * planner shell while still delegating route-level orchestration to the shell.
 */

import { computed, ref, watch } from "vue";

import { IconAdjustments, IconHistory, IconMinus, IconPlus, IconRedo, IconShuffle, IconUndo, IconX } from "../../../components/icons";
import {
  DENSE_FORM_INPUT_CLASS,
  UiDenseActionButton,
  UiDenseCompoundToggle,
  denseActionValueClass,
} from "../../../components/ui";
import type { GroupingExportOption } from "../classroomPlannerExportApi";
import type { RoomTemplate, Student } from "../classroomPlannerTypes";
import GroupBoard from "./GroupBoard.vue";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerExportActionGroup, {
  type PlannerExportOption,
  type PlannerExportOptionValue,
} from "./PlannerExportActionGroup.vue";
import PlannerSmartRulesSummaryStrip from "./PlannerSmartRulesSummaryStrip.vue";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import PlannerToolbarIconButton from "./PlannerToolbarIconButton.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(
  defineProps<{
    selectedStudentId?: string | null;
    availableTemplates?: RoomTemplate[];
    selectedTemplateId?: string | null;
    exportBusy?: boolean;
    exportStatusLabel?: string | null;
    exportErrorMessage?: string | null;
    canDownloadLatestExport?: boolean;
  }>(),
  {
    selectedStudentId: null,
    availableTemplates: () => [],
    selectedTemplateId: null,
    exportBusy: false,
    exportStatusLabel: null,
    exportErrorMessage: null,
    canDownloadLatestExport: false,
  },
);

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "new-grouping-draft"): void;
  (e: "open-history"): void;
  (e: "open-rules"): void;
  (e: "change-grouping-template", templateId: string | null): void;
  (e: "edit-roster"): void;
  (e: "export-default"): void;
  (e: "export-option", option: GroupingExportOption): void;
  (e: "download-latest-export"): void;
}>();

const state = useClassroomState();
const hasGroupingAssignments = computed(() => state.groupAssignments.length > 0);
const groupCount = computed(() => state.groups.length);
const removableGroupId = computed(() => {
  if (state.groups.length <= 1) {
    return null;
  }
  return [...state.groups].sort((left, right) => left.sort_order - right.sort_order).at(-1)?.id ?? null;
});
const isResetGroupingDialogOpen = ref(false);
const isExportStatusDismissed = ref(false);
const nearTeacherStudents = computed<Student[]>(() => {
  return (state.seatingPreferences ?? [])
    .filter((preference) => preference.near_teacher === true)
    .map((preference) => state.studentsById[preference.student_id] ?? null)
    .filter((student): student is Student => student !== null);
});
const exportOptions = computed<PlannerExportOption[]>(() => [
  {
    id: "xlsx",
    label: "Excel (.xlsx)",
    option: "xlsx",
    isDefault: true,
  },
  {
    id: "pdf",
    label: "PDF (A4 stående)",
    option: "pdf_a4_portrait",
  },
]);
const secondaryActionItems = computed(() => [
  {
    id: "history",
    label: "Historik",
    icon: IconHistory,
    disabled: state.isWorkspaceBusy,
    testId: "grouping-history",
    onSelect: () => emit("open-history"),
  },
  {
    id: "edit-roster",
    label: "Redigera klass",
    icon: IconAdjustments,
    disabled: state.isWorkspaceBusy,
    testId: "edit-grouping-roster",
    onSelect: () => emit("edit-roster"),
  },
]);

function onDragStart(event: DragEvent, studentId: string): void {
  if (state.isWorkspaceBusy) {
    return;
  }
  if (event.dataTransfer) {
    event.dataTransfer.setData("studentId", studentId);
    event.dataTransfer.effectAllowed = "move";
  }
}

function onDropToPool(event: DragEvent): void {
  if (state.isWorkspaceBusy) {
    return;
  }
  event.preventDefault();
  const studentId = event.dataTransfer?.getData("studentId");
  if (studentId) {
    state.removeStudentFromGroup(studentId);
  }
}

function onDragOver(event: DragEvent): void {
  if (state.isWorkspaceBusy) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
}

function changeGroupingTemplate(event: Event): void {
  const target = event.target;
  if (!(target instanceof HTMLSelectElement)) {
    return;
  }
  emit("change-grouping-template", target.value || null);
}

function openResetGroupingDialog(): void {
  if (state.isWorkspaceBusy || !hasGroupingAssignments.value) {
    return;
  }
  isResetGroupingDialogOpen.value = true;
}

function closeResetGroupingDialog(): void {
  isResetGroupingDialogOpen.value = false;
}

function confirmResetGroupingDraft(): void {
  state.clearGroupingAssignments();
  closeResetGroupingDialog();
}

function handleExportOption(option: PlannerExportOptionValue): void {
  emit("export-option", option as GroupingExportOption);
}

function decrementGroupCount(): void {
  if (state.isWorkspaceBusy || removableGroupId.value === null) {
    return;
  }
  state.removeGroup(removableGroupId.value);
}

function incrementGroupCount(): void {
  if (state.isWorkspaceBusy) {
    return;
  }
  state.addGroup();
}

watch(
  () => [props.exportStatusLabel, props.exportErrorMessage, props.canDownloadLatestExport] as const,
  () => {
    isExportStatusDismissed.value = false;
  },
);
</script>

<template>
  <div class="flex flex-col gap-3">
    <PlannerWorkspaceActionBar>
      <template
        v-if="availableTemplates.length > 0"
        #leading
      >
        <label class="block w-[12rem]">
          <select
            aria-label="Klassrum (valfritt)"
            :class="[DENSE_FORM_INPUT_CLASS, 'pr-8']"
            :value="selectedTemplateId ?? ''"
            data-test="grouping-template-select"
            @change="changeGroupingTemplate"
          >
            <option value="">
              Arbeta utan klassrum
            </option>
            <option
              v-for="template in availableTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} · {{ template.seats.length }} platser
            </option>
          </select>
        </label>
      </template>

      <div
        class="flex items-center [&>*+*]:-ml-px"
        data-test="grouping-history-cluster"
      >
        <PlannerToolbarIconButton
          label="Ångra"
          size="utility"
          group-position="start"
          data-test="undo-grouping"
          :disabled="!state.canUndo"
          @mousedown.prevent
          @click="void state.undoGroupingDraft()"
        >
          <IconUndo :size="16" />
        </PlannerToolbarIconButton>
        <PlannerToolbarIconButton
          label="Gör om"
          size="utility"
          group-position="end"
          data-test="redo-grouping"
          :disabled="!state.canRedo"
          @mousedown.prevent
          @click="void state.redoGroupingDraft()"
        >
          <IconRedo :size="16" />
        </PlannerToolbarIconButton>
      </div>
      <UiDenseActionButton
        label="Nytt utkast"
        title="Nytt grupputkast"
        data-test="new-grouping-draft"
        :disabled="state.isWorkspaceBusy"
        @click="emit('new-grouping-draft')"
      />
      <UiDenseActionButton
        label="Slumpa"
        data-test="randomize-groups"
        :disabled="state.isWorkspaceBusy"
        @click="state.randomizeGroups()"
      >
        <template #leading>
          <IconShuffle :size="16" />
        </template>
      </UiDenseActionButton>
      <UiDenseCompoundToggle
        root-test-id="grouping-smart-toggle"
        label="Smart"
        :model-value="state.draft?.smart_enabled ?? false"
        :disabled="state.isWorkspaceBusy"
        action-label="Regler"
        action-title="Öppna regler"
        :action-disabled="state.isWorkspaceBusy"
        action-test-id="grouping-open-rules"
        @update:model-value="state.setDraftSmartEnabled($event)"
        @action="emit('open-rules')"
      />
      <UiDenseActionButton
        label="Börja om"
        data-test="reset-grouping-draft"
        :disabled="state.isWorkspaceBusy || !hasGroupingAssignments"
        tone="danger"
        @click="openResetGroupingDialog"
      >
        Börja om
      </UiDenseActionButton>
      <div
        class="flex items-center"
        data-test="grouping-group-count-control"
      >
        <div class="flex items-center [&>*+*]:-ml-px">
          <PlannerToolbarIconButton
            label="Minska antal grupper"
            title="Ta bort sista gruppen"
            size="utility"
            group-position="start"
            data-test="decrement-group-count"
            :disabled="state.isWorkspaceBusy || removableGroupId === null"
            @click="decrementGroupCount"
          >
            <IconMinus :size="16" />
          </PlannerToolbarIconButton>
          <span
            :class="denseActionValueClass({ groupPosition: 'middle' })"
            data-test="group-count-value"
            title="Antal grupper"
          >
            {{ groupCount }}
          </span>
          <PlannerToolbarIconButton
            label="Öka antal grupper"
            title="Lägg till grupp"
            size="utility"
            group-position="end"
            data-test="increment-group-count"
            :disabled="state.isWorkspaceBusy"
            @click="incrementGroupCount"
          >
            <IconPlus :size="16" />
          </PlannerToolbarIconButton>
        </div>
      </div>
      <PlannerExportActionGroup
        :busy="exportBusy"
        :options="exportOptions"
        group-test-id="grouping-export-group"
        default-button-test-id="grouping-export-default"
        menu-trigger-test-id="grouping-export-menu-trigger"
        option-test-id-prefix="grouping-export-option"
        @export-default="emit('export-default')"
        @export-option="handleExportOption"
      />
      <PlannerToolbarOverflowMenu
        label="Fler gruppåtgärder"
        :items="secondaryActionItems"
        test-id="grouping-actions-menu"
      />
    </PlannerWorkspaceActionBar>

    <div
      v-if="!isExportStatusDismissed && (exportStatusLabel || exportErrorMessage || canDownloadLatestExport)"
      class="flex flex-wrap items-center gap-x-4 gap-y-1 border border-navy/30 bg-white px-3 py-2 text-xs"
      data-test="grouping-export-status-bar"
    >
      <p
        v-if="exportStatusLabel"
        class="text-navy"
        data-test="grouping-export-status"
      >
        {{ exportStatusLabel }}
      </p>
      <p
        v-if="exportErrorMessage"
        class="font-semibold text-burgundy"
        data-test="grouping-export-error"
      >
        {{ exportErrorMessage }}
      </p>
      <button
        v-if="canDownloadLatestExport"
        type="button"
        class="planner-link-button"
        data-test="grouping-export-download-latest"
        @click="emit('download-latest-export')"
      >
        Ladda ned igen
      </button>
      <button
        type="button"
        class="planner-icon-dismiss"
        aria-label="Stäng exportstatus"
        data-test="grouping-export-status-dismiss"
        @click="isExportStatusDismissed = true"
      >
        <IconX :size="14" />
      </button>
    </div>

    <div
      v-if="state.smartRuleHydrationStatus === 'error'"
      class="border border-amber-300/80 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-brutal-sm"
      data-test="grouping-smart-hydration-error"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <p>
          {{ state.smartRuleHydrationMessage }}
        </p>
        <button
          type="button"
          class="btn-ghost planner-btn-alert planner-btn-ghost-sm"
          data-test="grouping-smart-retry-hydration"
          @click="void state.retrySmartRuleHydration()"
        >
          Försök igen
        </button>
      </div>
    </div>

    <PlannerSmartRulesSummaryStrip
      :near-teacher-students="nearTeacherStudents"
      :relationship-rules="state.relationshipRules"
      :students-by-id="state.studentsById"
    />

    <div class="grid gap-3 xl:grid-cols-[240px_minmax(0,1fr)] xl:items-stretch">
      <PlannerStudentPool
        title="Ej grupperade"
        :students="state.ungroupedStudents"
        :selected-student-id="selectedStudentId"
        :disabled="state.isWorkspaceBusy"
        empty-label="Alla elever ligger i grupp"
        root-test-id="grouping-student-pool"
        @student-selected="emit('student-selected', $event)"
        @student-dragstart="onDragStart($event.event, $event.studentId)"
        @pool-dragover="onDragOver"
        @pool-drop="onDropToPool"
      />

      <GroupBoard
        :selected-student-id="selectedStudentId"
        @student-selected="emit('student-selected', $event)"
      />
    </div>

    <PlannerConfirmationDialog
      v-if="isResetGroupingDialogOpen"
      eyebrow="Börja om grupper"
      title="Töm gruppindelningen?"
      message="Det här rensar gruppplaceringarna i det aktuella grupputkastet och flyttar tillbaka alla elever till Ej grupperade. Själva utkastet finns kvar."
      confirm-label="Börja om"
      @cancel="closeResetGroupingDialog"
      @confirm="confirmResetGroupingDraft"
    />
  </div>
</template>
