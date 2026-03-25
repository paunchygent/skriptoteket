<script setup lang="ts">
/**
 * Grouping workspace pane.
 *
 * This component composes the grouping-only student pool, action row, and
 * group board. It keeps the task-specific grouping chrome outside the global
 * planner shell while still delegating route-level orchestration to the shell.
 */

import { computed, ref } from "vue";

import { IconHistory, IconRedo, IconSettings, IconShuffle, IconUndo } from "../../../components/icons";
import type { RoomTemplate } from "../classroomPlannerTypes";
import GroupBoard from "./GroupBoard.vue";
import PlannerConfirmationDialog from "./PlannerConfirmationDialog.vue";
import PlannerStudentPool from "./PlannerStudentPool.vue";
import PlannerToolbarIconButton from "./PlannerToolbarIconButton.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import PlannerWorkspaceActionBar from "./PlannerWorkspaceActionBar.vue";
import { useClassroomState } from "../useClassroomState";

withDefaults(
  defineProps<{
    selectedStudentId?: string | null;
    availableTemplates?: RoomTemplate[];
    selectedTemplateId?: string | null;
  }>(),
  {
    selectedStudentId: null,
    availableTemplates: () => [],
    selectedTemplateId: null,
  },
);

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "new-grouping-draft"): void;
  (e: "open-history"): void;
  (e: "change-grouping-template", templateId: string | null): void;
  (e: "edit-roster"): void;
}>();

const state = useClassroomState();
const hasGroupingAssignments = computed(() => state.groupAssignments.length > 0);
const isResetGroupingDialogOpen = ref(false);
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
    icon: IconSettings,
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
</script>

<template>
  <div class="flex flex-col gap-3">
    <PlannerWorkspaceActionBar>
      <template
        v-if="availableTemplates.length > 0"
        #leading
      >
        <label class="block w-[12rem] space-y-1">
          <span class="block text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Klassrum (valfritt)
          </span>
          <select
            aria-label="Klassrum (valfritt)"
            class="w-full border border-navy/20 bg-white px-3 py-2 text-sm text-navy"
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

      <PlannerToolbarIconButton
        label="Ångra"
        class="2xl:hidden"
        data-test="undo-grouping"
        :disabled="!state.canUndo"
        @mousedown.prevent
        @click="void state.undoGroupingDraft()"
      >
        <IconUndo :size="18" />
      </PlannerToolbarIconButton>
      <button
        type="button"
        class="btn-ghost hidden border-navy/30 bg-white shadow-none 2xl:inline-flex"
        :disabled="!state.canUndo"
        @mousedown.prevent
        @click="void state.undoGroupingDraft()"
      >
        Ångra
      </button>
      <PlannerToolbarIconButton
        label="Gör om"
        class="2xl:hidden"
        data-test="redo-grouping"
        :disabled="!state.canRedo"
        @mousedown.prevent
        @click="void state.redoGroupingDraft()"
      >
        <IconRedo :size="18" />
      </PlannerToolbarIconButton>
      <button
        type="button"
        class="btn-ghost hidden border-navy/30 bg-white shadow-none 2xl:inline-flex"
        :disabled="!state.canRedo"
        @mousedown.prevent
        @click="void state.redoGroupingDraft()"
      >
        Gör om
      </button>
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
        data-test="new-grouping-draft"
        :disabled="state.isWorkspaceBusy"
        @click="emit('new-grouping-draft')"
      >
        Nytt grupputkast
      </button>
      <button
        type="button"
        class="btn-ghost inline-flex items-center gap-2 border-navy/30 bg-white shadow-none disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
        data-test="randomize-groups"
        :disabled="state.isWorkspaceBusy"
        @click="state.randomizeGroups()"
      >
        <IconShuffle :size="16" />
        <span>Slumpa</span>
      </button>
      <button
        type="button"
        class="btn-ghost border-navy/30 bg-white shadow-none disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
        data-test="reset-grouping-draft"
        :disabled="state.isWorkspaceBusy || !hasGroupingAssignments"
        @click="openResetGroupingDialog"
      >
        Börja om
      </button>
      <button
        type="button"
        class="btn-primary"
        data-test="add-group"
        :disabled="state.isWorkspaceBusy"
        @click="state.addGroup()"
      >
        Lägg till grupp
      </button>
      <PlannerToolbarOverflowMenu
        label="Fler gruppåtgärder"
        :items="secondaryActionItems"
        test-id="grouping-actions-menu"
      />
    </PlannerWorkspaceActionBar>

    <div class="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)] xl:items-stretch">
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
