<script setup lang="ts">
/**
 * Draft group bucket card.
 *
 * This component renders one mutable draft-scoped group inside the classroom
 * planner. It keeps drag-and-drop assignment local to the card while exposing
 * explicit controls for rename, reorder, removal, and student selection so the
 * metadata drawer can stay outside the card grid.
 */

import { ref, watch } from "vue";

import { IconTrash, IconX } from "../../../components/icons";
import type { DraftGroup, Student } from "../classroomPlannerTypes";

const props = defineProps<{
  group: DraftGroup;
  students: Student[];
  canMoveUp: boolean;
  canMoveDown: boolean;
  selectedStudentId?: string | null;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: "student-dropped", studentId: string, groupId: string): void;
  (e: "student-removed", studentId: string): void;
  (e: "group-renamed", groupId: string, name: string): void;
  (e: "group-moved", groupId: string, offset: number): void;
  (e: "group-removed", groupId: string): void;
  (e: "student-selected", studentId: string): void;
}>();

const editableName = ref(props.group.name);

watch(
  () => props.group.name,
  (name) => {
    editableName.value = name;
  },
);

function onDrop(event: DragEvent): void {
  if (props.disabled) {
    return;
  }
  event.preventDefault();
  const studentId = event.dataTransfer?.getData("studentId");
  if (studentId) {
    emit("student-dropped", studentId, props.group.id);
  }
}

function onDragOver(event: DragEvent): void {
  if (props.disabled) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
}

function onDragStart(event: DragEvent, student: Student): void {
  if (props.disabled) {
    return;
  }
  if (event.dataTransfer) {
    event.dataTransfer.setData("studentId", student.id);
    event.dataTransfer.effectAllowed = "move";
  }
}

function commitName(): void {
  if (props.disabled) {
    return;
  }
  if (editableName.value.trim() === props.group.name.trim()) {
    return;
  }
  emit("group-renamed", props.group.id, editableName.value);
}
</script>

<template>
  <div
    data-test="group-card"
    class="flex self-start flex-col border border-navy bg-white p-3 shadow-brutal-sm"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <div class="flex items-center justify-between gap-2 border-b border-navy/20 pb-2">
      <div class="min-w-0 flex-1">
        <input
          v-model="editableName"
          type="text"
          data-test="group-name-input"
          class="h-[36px] w-full border border-navy/30 bg-canvas px-3 text-sm font-semibold text-navy shadow-none"
          :disabled="props.disabled"
          @blur="commitName"
          @keyup.enter="commitName"
        >
      </div>
      <div class="flex shrink-0 items-center gap-1">
        <button
          type="button"
          aria-label="Flytta grupp upp"
          data-test="move-group-up"
          class="btn-ghost planner-btn-ghost-canvas planner-btn-icon-lg"
          :disabled="props.disabled || !canMoveUp"
          @click="emit('group-moved', group.id, -1)"
        >
          ↑
        </button>
        <button
          type="button"
          aria-label="Flytta grupp ned"
          data-test="move-group-down"
          class="btn-ghost planner-btn-ghost-canvas planner-btn-icon-lg"
          :disabled="props.disabled || !canMoveDown"
          @click="emit('group-moved', group.id, 1)"
        >
          ↓
        </button>
        <button
          type="button"
          data-test="remove-group"
          class="btn-ghost planner-btn-danger planner-btn-icon-lg"
          :disabled="props.disabled"
          aria-label="Ta bort grupp"
          @click="emit('group-removed', group.id)"
        >
          <IconTrash :size="14" />
        </button>
      </div>
    </div>

    <div class="mt-2.5 flex flex-col gap-1.5">
      <div
        v-for="student in students"
        :key="student.id"
        class="flex min-h-[44px] items-start justify-between gap-2.5 border px-3 py-1.5 text-left transition-colors"
        :class="selectedStudentId === student.id ? 'border-burgundy bg-burgundy/10 text-burgundy' : 'border-navy bg-white text-navy hover:bg-canvas'"
        :draggable="!props.disabled"
        @dragstart="onDragStart($event, student)"
      >
        <button
          type="button"
          class="planner-row-select-button"
          :disabled="props.disabled"
          @click="emit('student-selected', student.id)"
        >
          <div
            data-test="group-student-name"
            class="break-words text-sm font-semibold leading-snug"
          >
            {{ student.display_name }}
          </div>
        </button>
        <button
          type="button"
          class="planner-row-remove-button"
          :disabled="props.disabled"
          :aria-label="`Ta bort ${student.display_name} från grupp`"
          @click.stop="emit('student-removed', student.id)"
        >
          <IconX :size="14" />
        </button>
      </div>

      <div
        v-if="students.length === 0"
        class="flex min-h-[88px] items-center justify-center border border-dashed border-navy/30 bg-canvas px-4 py-4 text-center text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/40"
      >
        Släpp elever här
      </div>
    </div>
  </div>
</template>
