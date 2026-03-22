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

import GroupCard from "./GroupCard.vue";
import { useClassroomState } from "../useClassroomState";

const props = defineProps<{
  selectedStudentId?: string | null;
}>();

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "new-grouping-draft"): void;
}>();

const state = useClassroomState();

const orderedGroups = computed(() => [...state.groups].sort((left, right) => left.sort_order - right.sort_order));

function onDragStart(event: DragEvent, studentId: string): void {
  if (event.dataTransfer) {
    event.dataTransfer.setData("studentId", studentId);
    event.dataTransfer.effectAllowed = "move";
  }
}

function onDropToPool(event: DragEvent): void {
  event.preventDefault();
  const studentId = event.dataTransfer?.getData("studentId");
  if (studentId) {
    state.removeStudentFromGroup(studentId);
  }
}

function onDragOver(event: DragEvent): void {
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
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
          draggable="true"
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
      <div class="flex flex-col gap-3 border border-navy bg-white p-4 shadow-brutal-sm md:flex-row md:items-center md:justify-between">
        <div class="space-y-1">
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Gruppstruktur
          </p>
          <h3 class="font-serif text-xl text-navy">
            Arbetsgrupper
          </h3>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-white shadow-none"
            data-test="new-grouping-draft"
            @click="emit('new-grouping-draft')"
          >
            Nytt grupputkast
          </button>
          <button
            type="button"
            class="btn-ghost border-navy/30 bg-white shadow-none"
            data-test="randomize-groups"
            @click="state.randomizeGroups()"
          >
            Slumpa
          </button>
          <button
            type="button"
            class="btn-primary"
            data-test="add-group"
            @click="state.addGroup()"
          >
            Lägg till grupp
          </button>
        </div>
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
