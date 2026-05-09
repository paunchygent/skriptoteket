<script setup lang="ts">
/**
 * Seat node renderer.
 *
 * This component renders one seat on the classroom canvas and keeps seat-level
 * drag-and-drop interaction local. In the seating workspace, student tokens are
 * draggable and removable, but no longer support click activation.
 */

import type { Component } from "vue";

import RoomSeatToken from "./RoomSeatToken.vue";
import { IconKeepApart, IconKeepNear, IconLock, IconTeacherAnchor } from "../../../components/icons";
import type { Seat, Student } from "../classroomPlannerTypes";
import type { SmartRuleMarkerKind, SmartRuleSymbolMarker } from "../classroomPlannerSeatRuleMarkers";
import { getSeatFrameStyle } from "../roomSeatPresentation";

const props = defineProps<{
  seat: Seat;
  student: Student | null;
  selected?: boolean;
  markers?: SmartRuleSymbolMarker[];
  fixed?: boolean;
  fixedSeatTitle?: string | null;
}>();

const markerIconByKind: Record<SmartRuleMarkerKind, Component> = {
  "fixed-seat": IconLock,
  "keep-apart": IconKeepApart,
  "keep-near": IconKeepNear,
  "near-teacher": IconTeacherAnchor,
};

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
    :class="[
      student ? 'cursor-grab hover:-translate-y-0.5' : '',
      (markers ?? []).length > 0 ? 'z-30' : 'z-10',
    ]"
    :style="getSeatFrameStyle(seat)"
    :draggable="Boolean(student)"
    @dragover="onDragOver"
    @drop="onDrop"
    @dragstart="onDragStart"
  >
    <div
      v-if="(markers ?? []).length > 0"
      class="pointer-events-none absolute bottom-[calc(100%_-_0.25rem)] left-1/2 z-30 flex -translate-x-1/2 flex-col-reverse items-center justify-end gap-0.5"
      :aria-label="markers?.map((marker) => marker.label).join(' ')"
      :title="markers?.map((marker) => marker.label).join(' ')"
      :data-test="`seat-markers-${seat.id}`"
    >
      <span
        v-for="marker in markers"
        :key="marker.id"
        class="inline-flex h-5 w-5 shrink-0 items-center justify-center border text-[9px] shadow-brutal-sm"
        :class="{
          'border-success bg-success text-white': marker.tone === 'success',
          'border-warning bg-warning text-navy': marker.tone === 'warning',
          'border-error bg-error text-white': marker.tone === 'error',
        }"
        :title="marker.label"
        :aria-label="marker.label"
        :data-test="`seat-rule-marker-${seat.id}-${marker.kind}-${marker.tone}`"
      >
        <component
          :is="markerIconByKind[marker.kind]"
          :size="12"
        />
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
