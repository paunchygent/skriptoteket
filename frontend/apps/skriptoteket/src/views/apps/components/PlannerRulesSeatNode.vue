<script setup lang="ts">
/**
 * Rules-workspace seat node.
 *
 * This component renders one clickable student tile on the rules map with
 * ordered multi-select feedback, rule markers, and no seating drag/drop
 * behavior.
 */

import RoomSeatToken from "./RoomSeatToken.vue";
import type { Seat, Student } from "../classroomPlannerTypes";
import { getSeatFrameStyle } from "../roomSeatPresentation";

withDefaults(defineProps<{
  seat: Seat;
  student: Student | null;
  selected?: boolean;
  selectionOrder?: number | null;
  markers?: string[];
  interactive?: boolean;
}>(), {
  selected: false,
  selectionOrder: null,
  markers: () => [],
  interactive: true,
});

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
}>();
</script>

<template>
  <div
    class="absolute transition-transform"
    :class="student && interactive ? 'cursor-pointer hover:-translate-y-0.5' : ''"
    :style="getSeatFrameStyle(seat)"
    :data-test="`rules-seat-node-${seat.id}`"
  >
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
      class="pointer-events-none absolute -left-2 -top-2 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-burgundy bg-white text-[11px] font-semibold text-burgundy shadow-brutal-sm"
      :data-test="`rules-seat-order-${seat.id}`"
    >
      {{ selectionOrder }}
    </span>

    <button
      v-if="student"
      type="button"
      class="h-full w-full"
      :disabled="!interactive"
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
  </div>
</template>
