<script setup lang="ts">
/**
 * Rules-workspace seat node.
 *
 * This component renders one clickable student tile on the rules map with
 * ordered multi-select feedback, rule markers, and no seating drag/drop
 * behavior.
 */

import RoomSeatToken from "./RoomSeatToken.vue";
import { IconLock } from "../../../components/icons";
import type { Seat, Student } from "../classroomPlannerTypes";
import { getSeatFrameStyle } from "../roomSeatPresentation";

const props = withDefaults(defineProps<{
  seat: Seat;
  student: Student | null;
  selected?: boolean;
  selectionOrder?: number | null;
  markers?: string[];
  interactive?: boolean;
  fixed?: boolean;
  fixedSeatTitle?: string | null;
  fixedSeatActive?: boolean;
  pendingFixedSeatStudentId?: string | null;
  pendingFixedSeatSeatId?: string | null;
  pendingFixedSeatPreviewTitle?: string | null;
}>(), {
  selected: false,
  selectionOrder: null,
  markers: () => [],
  interactive: true,
  fixed: false,
  fixedSeatTitle: null,
  fixedSeatActive: false,
  pendingFixedSeatStudentId: null,
  pendingFixedSeatSeatId: null,
  pendingFixedSeatPreviewTitle: null,
});

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
  (e: "seat-selected", seatId: string): void;
}>();

function handleSeatClick(): void {
  if (!props.fixedSeatActive) {
    if (props.student) {
      emit("student-selected", props.student.id);
    }
    return;
  }
  if (props.pendingFixedSeatSeatId === props.seat.id) {
    emit("seat-selected", props.seat.id);
    return;
  }
  if (props.pendingFixedSeatStudentId) {
    emit("seat-selected", props.seat.id);
    return;
  }
  if (props.student) {
    emit("student-selected", props.student.id);
    return;
  }
  emit("seat-selected", props.seat.id);
}
</script>

<template>
  <div
    class="absolute transition-transform"
    :class="interactive ? 'cursor-pointer hover:-translate-y-0.5' : ''"
    :style="getSeatFrameStyle(seat)"
    :data-test="`rules-seat-node-${seat.id}`"
  >
    <span
      v-if="fixed"
      class="pointer-events-none absolute -right-2 -top-2 z-20 flex h-6 w-6 items-center justify-center rounded-full border border-action bg-action text-white shadow-brutal-sm"
      :title="fixedSeatTitle ?? undefined"
      :aria-label="fixedSeatTitle ?? 'Fast plats'"
      :data-test="`rules-seat-fixed-lock-${seat.id}`"
    >
      <IconLock :size="13" />
    </span>

    <span
      v-if="pendingFixedSeatPreviewTitle"
      class="pointer-events-none absolute -right-2 -top-2 z-20 flex h-6 w-6 items-center justify-center rounded-full border-2 border-dashed border-action bg-white text-action shadow-brutal-sm"
      :title="pendingFixedSeatPreviewTitle"
      :aria-label="pendingFixedSeatPreviewTitle"
      :data-test="`rules-seat-pending-lock-${seat.id}`"
    >
      <IconLock :size="13" />
    </span>

    <div
      v-if="markers.length > 0"
      class="pointer-events-none absolute -top-7 left-1/2 z-10 flex w-max max-w-none -translate-x-1/2 flex-nowrap items-center gap-0.5 whitespace-nowrap"
    >
      <span
        v-for="marker in markers"
        :key="marker"
        class="inline-flex h-3.5 shrink-0 items-center border border-navy/20 bg-canvas px-1.5 text-[8px] font-semibold uppercase tracking-[0.08em] text-navy/70"
      >
        {{ marker }}
      </span>
    </div>

    <span
      v-if="selectionOrder !== null"
      class="pointer-events-none absolute -left-2 -top-2 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-action bg-white text-[11px] font-semibold text-action shadow-brutal-sm"
      :data-test="`rules-seat-order-${seat.id}`"
    >
      {{ selectionOrder }}
    </span>

    <button
      v-if="student || fixedSeatActive"
      type="button"
      class="h-full w-full"
      :disabled="!interactive"
      :aria-label="fixedSeatTitle ?? undefined"
      @click="handleSeatClick"
    >
      <RoomSeatToken
        :seat-id="seat.id"
        :student-name="student?.display_name ?? null"
        :selected="selected"
      />
    </button>

    <RoomSeatToken
      v-else
      :seat-id="seat.id"
      :selected="selected"
    />
  </div>
</template>
