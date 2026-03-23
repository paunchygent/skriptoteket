<script setup lang="ts">
/**
 * Group planning board.
 *
 * This component renders the draft-scoped grouping workspace: an ungrouped
 * student pool plus the ordered group buckets. It delegates mutations back to
 * the store-facing planner shell so autosave, validation, and metadata state
 * remain centralized.
 */

import { computed } from "vue";

import { IconHistory, IconRedo, IconSettings, IconShuffle, IconUndo } from "../../../components/icons";
import type { RoomTemplate } from "../classroomPlannerTypes";
import GroupCard from "./GroupCard.vue";
import PlannerToolbarIconButton from "./PlannerToolbarIconButton.vue";
import PlannerToolbarOverflowMenu from "./PlannerToolbarOverflowMenu.vue";
import { useClassroomState } from "../useClassroomState";

const props = defineProps<{
  selectedStudentId?: string | null;
  availableTemplates?: RoomTemplate[];
  selectedTemplateId?: string | null;
}>();

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "new-grouping-draft"): void;
  (e: "open-history"): void;
  (e: "change-grouping-template", templateId: string | null): void;
  (e: "edit-roster"): void;
}>();

const state = useClassroomState();

const orderedGroups = computed(() => [...state.groups].sort((left, right) => left.sort_order - right.sort_order));
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
</script>

<template>
  <div class="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
    <aside
      class="flex min-h-[320px] flex-col border border-navy bg-white p-4 shadow-brutal-sm"
      @dragover="onDragOver"
      @drop="onDropToPool"
    >
      <div class="flex items-end justify-between gap-3 border-b border-navy/20 pb-3">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Studentpool
          </p>
          <h3 class="font-serif text-xl text-navy">
            Ej grupperade
          </h3>
        </div>
        <span class="border border-navy bg-canvas px-2 py-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/70">
          {{ state.ungroupedStudents.length }}
        </span>
      </div>

      <div class="mt-4 flex flex-1 flex-col gap-2 overflow-y-auto">
        <button
          v-for="student in state.ungroupedStudents"
          :key="student.id"
          type="button"
          class="flex items-start justify-between gap-3 border px-3 py-2 text-left transition-colors"
          :class="props.selectedStudentId === student.id ? 'border-burgundy bg-burgundy/10 text-burgundy' : 'border-navy bg-white text-navy hover:bg-canvas'"
          :disabled="state.isWorkspaceBusy"
          :draggable="!state.isWorkspaceBusy"
          @click="emit('student-selected', student.id)"
          @dragstart="onDragStart($event, student.id)"
        >
          <div class="min-w-0">
            <div class="truncate text-sm font-semibold">
              {{ student.display_name }}
            </div>
          </div>
        </button>

        <div
          v-if="state.ungroupedStudents.length === 0"
          class="flex flex-1 items-center justify-center border border-dashed border-navy/30 bg-canvas px-4 py-6 text-center text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/40"
        >
          Alla elever ligger i grupp
        </div>
      </div>
    </aside>

    <section class="space-y-4">
      <div class="flex flex-wrap items-end justify-end gap-2 border border-navy bg-white p-4 shadow-brutal-sm">
        <label
          v-if="props.availableTemplates && props.availableTemplates.length > 0"
          class="block min-w-[16rem]"
        >
          <select
            aria-label="Klassrum (valfritt)"
            class="w-full border border-navy/20 bg-white px-3 py-2 text-sm text-navy"
            :value="props.selectedTemplateId ?? ''"
            data-test="grouping-template-select"
            @change="changeGroupingTemplate"
          >
            <option value="">
              Arbeta utan klassrum
            </option>
            <option
              v-for="template in props.availableTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} · {{ template.seats.length }} platser
            </option>
          </select>
        </label>
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
      </div>

      <div class="grid items-start gap-4 md:grid-cols-2 2xl:grid-cols-3">
        <GroupCard
          v-for="(group, index) in orderedGroups"
          :key="group.id"
          :group="group"
          :students="state.studentsByGroupId[group.id] ?? []"
          :can-move-up="index > 0"
          :can-move-down="index < orderedGroups.length - 1"
          :selected-student-id="props.selectedStudentId"
          :disabled="state.isWorkspaceBusy"
          @student-dropped="state.assignStudentToGroup"
          @student-removed="state.removeStudentFromGroup"
          @group-renamed="state.renameGroup"
          @group-moved="state.moveGroup"
          @group-removed="state.removeGroup"
          @student-selected="emit('student-selected', $event)"
        />
      </div>
    </section>
  </div>
</template>
