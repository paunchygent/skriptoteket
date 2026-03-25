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
    class="flex self-start flex-col border border-navy bg-white p-4 shadow-brutal-sm transition-transform transition-shadow hover:-translate-y-0.5 hover:shadow-brutal"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <div class="flex items-center justify-between gap-3 border-b border-navy/20 pb-3">
      <div class="min-w-0 flex-1 space-y-2">
        <label class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
          Gruppnamn
        </label>
        <input
          v-model="editableName"
          type="text"
          class="w-full border border-navy/30 bg-canvas px-2 py-2 text-sm font-semibold text-navy shadow-none"
          :disabled="props.disabled"
          @blur="commitName"
          @keyup.enter="commitName"
        >
      </div>
      <div class="flex items-center gap-1">
        <button
          type="button"
          aria-label="Flytta grupp upp"
          data-test="move-group-up"
          class="btn-ghost h-[28px] w-[28px] px-0 py-0 shadow-none border-navy/30 bg-canvas"
          :disabled="props.disabled || !canMoveUp"
          @click="emit('group-moved', group.id, -1)"
        >
          ↑
        </button>
        <button
          type="button"
          aria-label="Flytta grupp ned"
          data-test="move-group-down"
          class="btn-ghost h-[28px] w-[28px] px-0 py-0 shadow-none border-navy/30 bg-canvas"
          :disabled="props.disabled || !canMoveDown"
          @click="emit('group-moved', group.id, 1)"
        >
          ↓
        </button>
        <button
          type="button"
          class="btn-ghost h-[28px] w-[28px] px-0 py-0 shadow-none border-burgundy/40 bg-white text-burgundy"
          :disabled="props.disabled"
          aria-label="Ta bort grupp"
          @click="emit('group-removed', group.id)"
        >
          <IconTrash :size="14" />
        </button>
      </div>
    </div>

    <div class="mt-3 flex flex-col gap-2">
      <div
        v-for="student in students"
        :key="student.id"
        class="flex min-h-[52px] items-start justify-between gap-3 border px-3 py-2 text-left transition-colors"
        :class="selectedStudentId === student.id ? 'border-burgundy bg-burgundy/10 text-burgundy' : 'border-navy bg-white text-navy hover:bg-canvas'"
        :draggable="!props.disabled"
        @dragstart="onDragStart($event, student)"
      >
        <button
          type="button"
          class="min-w-0 flex-1 text-left"
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
          class="mt-0.5 shrink-0 text-burgundy opacity-60 transition-opacity hover:opacity-100"
          :disabled="props.disabled"
          :aria-label="`Ta bort ${student.display_name} från grupp`"
          @click.stop="emit('student-removed', student.id)"
        >
          <IconX :size="14" />
        </button>
      </div>

      <div
        v-if="students.length === 0"
        class="flex min-h-[112px] items-center justify-center border border-dashed border-navy/30 bg-canvas px-4 py-6 text-center text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/40"
      >
        Släpp elever här
      </div>
    </div>
  </div>
</template>
