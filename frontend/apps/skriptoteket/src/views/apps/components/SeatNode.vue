<script setup lang="ts">
/**
 * Seat node renderer.
 *
 * This component renders one seat on the classroom canvas and keeps seat-level
 * drag-and-drop interaction local. In the seating workspace, student tokens are
 * draggable and removable, but no longer support click activation.
 */

import RoomSeatToken from "./RoomSeatToken.vue";
import { IconLock } from "../../../components/icons";
import type { Seat, Student } from "../classroomPlannerTypes";
import { getSeatFrameStyle } from "../roomSeatPresentation";

const props = defineProps<{
  seat: Seat;
  student: Student | null;
  selected?: boolean;
  markers?: string[];
  fixed?: boolean;
  fixedSeatTitle?: string | null;
}>();

const emit = defineEmits<{
  (e: "student-dropped", studentId: string, seatId: string): void;
  (e: "student-removed", studentId: string): void;
  (e: "swap-requested", studentIdA: string, studentIdB: string): void;
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
  if (!event.dataTransfer || !props.student) {
    return;
  }
  event.dataTransfer.setData("studentId", props.student.id);
  event.dataTransfer.effectAllowed = "move";

  // The seat node is inside a CSS transform:scale() surface.
  // Browsers capture drag images before applying ancestor transforms,
  // producing a mispositioned or blank ghost. Fix: clone the element
  // outside the transform context and use it as the explicit drag image.
  const el = event.currentTarget;
  if (!(el instanceof HTMLElement)) {
    return;
  }
  const clone = el.cloneNode(true);
  if (!(clone instanceof HTMLElement)) {
    return;
  }
  Object.assign(clone.style, {
    position: "fixed",
    top: "-9999px",
    left: "0",
    width: `${el.offsetWidth}px`,
    height: `${el.offsetHeight}px`,
    pointerEvents: "none",
  });
  document.body.appendChild(clone);
  event.dataTransfer.setDragImage(clone, el.offsetWidth / 2, el.offsetHeight / 2);
  requestAnimationFrame(() => {
    document.body.removeChild(clone);
  });
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
    <div
      v-if="(markers ?? []).length > 0"
      class="pointer-events-none absolute -top-5 left-1/2 z-10 flex -translate-x-1/2 flex-wrap justify-center gap-1"
      :data-test="`seat-markers-${seat.id}`"
    >
      <span
        v-for="marker in markers"
        :key="marker"
        class="border border-navy/20 bg-canvas px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/70"
      >
        {{ marker }}
      </span>
    </div>

    <span
      v-if="fixed"
      class="pointer-events-none absolute -right-2 -top-2 z-20 flex h-6 w-6 items-center justify-center rounded-full border border-action bg-action text-white shadow-brutal-sm"
      :title="fixedSeatTitle ?? undefined"
      :aria-label="fixedSeatTitle ?? 'Fast plats'"
      :data-test="`seat-fixed-lock-${seat.id}`"
    >
      <IconLock :size="13" />
    </span>

    <div
      v-if="student"
      class="h-full w-full"
    >
      <RoomSeatToken
        :seat-id="seat.id"
        :student-name="student.display_name"
        :selected="selected"
      />
    </div>
    <RoomSeatToken
      v-else
      :seat-id="seat.id"
      :selected="selected"
    />

    <button
      v-if="student"
      type="button"
      class="planner-marker-button"
      @click.stop="emit('student-removed', student.id)"
    >
      ×
    </button>
  </div>
</template>
