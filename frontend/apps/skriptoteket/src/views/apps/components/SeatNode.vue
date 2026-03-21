<script setup lang="ts">
/**
 * Seat node renderer.
 *
 * This component renders one seat on the classroom canvas and keeps seat-level
 * drag-and-drop interaction local. It also emits student selection so the
 * planner shell can open the metadata drawer without coupling the seat visuals
 * to the form logic.
 */

import type { Seat, Student } from "../classroomPlannerTypes";

const props = defineProps<{
  seat: Seat;
  student: Student | null;
  selected?: boolean;
}>();

const emit = defineEmits<{
  (e: "student-dropped", studentId: string, seatId: string): void;
  (e: "student-removed", studentId: string): void;
  (e: "swap-requested", studentIdA: string, studentIdB: string): void;
  (e: "student-selected", studentId: string): void;
}>();

function onDrop(event: DragEvent): void {
  event.preventDefault();
  const sourceStudentId = event.dataTransfer?.getData("studentId");
  if (!sourceStudentId) {
    return;
  }

  if (props.student && props.student.id !== sourceStudentId) {
    emit("swap-requested", sourceStudentId, props.student.id);
    return;
  }

  emit("student-dropped", sourceStudentId, props.seat.id);
}

function onDragOver(event: DragEvent): void {
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
}

function onDragStart(event: DragEvent): void {
  if (event.dataTransfer && props.student) {
    event.dataTransfer.setData("studentId", props.student.id);
    event.dataTransfer.effectAllowed = "move";
  }
}
</script>

<template>
  <div
    class="absolute flex items-center justify-center border transition-transform transition-shadow"
    :class="[
      selected ? 'border-burgundy bg-burgundy/10 text-burgundy shadow-brutal' : '',
      student ? 'cursor-grab bg-white text-navy shadow-brutal-sm hover:-translate-y-0.5 hover:shadow-brutal' : 'border-navy/30 bg-white/70 text-navy/40 border-dashed',
    ]"
    :style="{
      left: `${seat.x + 12}px`,
      top: `${seat.y + 12}px`,
      width: '72px',
      height: '72px',
    }"
    :draggable="Boolean(student)"
    @dragover="onDragOver"
    @drop="onDrop"
    @dragstart="onDragStart"
  >
    <button
      v-if="student"
      type="button"
      class="flex h-full w-full flex-col items-center justify-center px-1 text-center"
      @click="emit('student-selected', student.id)"
    >
      <span class="line-clamp-2 text-xs font-semibold leading-tight">
        {{ student.display_name }}
      </span>
      <span class="mt-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
        {{ seat.id }}
      </span>
    </button>
    <div
      v-else
      class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)]"
    >
      {{ seat.id }}
    </div>

    <button
      v-if="student"
      type="button"
      class="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center border border-burgundy bg-white text-[11px] font-semibold text-burgundy"
      @click.stop="emit('student-removed', student.id)"
    >
      ×
    </button>
  </div>
</template>
