<script setup lang="ts">
/**
 * Seat node renderer.
 *
 * This component renders one seat on the classroom canvas and keeps seat-level
 * drag-and-drop interaction local. It also emits student selection so the
 * planner shell can open the metadata drawer without coupling the seat visuals
 * to the form logic.
 */

import RoomSeatToken from "./RoomSeatToken.vue";
import type { Seat, Student } from "../classroomPlannerTypes";
import { getSeatFrameStyle } from "../roomSeatPresentation";

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
    class="absolute transition-transform transition-shadow"
    :class="student ? 'cursor-grab hover:-translate-y-0.5' : ''"
    :style="getSeatFrameStyle(seat)"
    :draggable="Boolean(student)"
    @dragover="onDragOver"
    @drop="onDrop"
    @dragstart="onDragStart"
  >
    <button
      v-if="student"
      type="button"
      class="h-full w-full"
      @click="emit('student-selected', student.id)"
    >
      <RoomSeatToken
        :seat-id="seat.id"
        :student-name="student.display_name"
        :selected="selected"
      />
    </button>
    <RoomSeatToken
      v-else
      :seat-id="seat.id"
      :selected="selected"
    />

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
