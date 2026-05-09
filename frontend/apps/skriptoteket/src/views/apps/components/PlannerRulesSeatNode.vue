<script setup lang="ts">
/**
 * Rules-workspace seat node.
 *
 * This component renders one clickable student tile on the rules map with
 * ordered multi-select feedback, rule markers, and no seating drag/drop
 * behavior.
 */

import type { Component } from "vue";

import RoomSeatToken from "./RoomSeatToken.vue";
import { IconKeepApart, IconKeepNear, IconLock, IconTeacherAnchor } from "../../../components/icons";
import type { Seat, Student } from "../classroomPlannerTypes";
import type { SmartRuleMarkerKind, SmartRuleSymbolMarker } from "../classroomPlannerSeatRuleMarkers";
import { getSeatFrameStyle } from "../roomSeatPresentation";

const props = withDefaults(defineProps<{
  seat: Seat;
  student: Student | null;
  selected?: boolean;
  selectionOrder?: number | null;
  markers?: SmartRuleSymbolMarker[];
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

const markerIconByKind: Record<SmartRuleMarkerKind, Component> = {
  "fixed-seat": IconLock,
  "keep-apart": IconKeepApart,
  "keep-near": IconKeepNear,
  "near-teacher": IconTeacherAnchor,
};

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
    :class="[
      interactive ? 'cursor-pointer hover:-translate-y-0.5' : '',
      markers.length > 0 ? 'z-30' : 'z-10',
    ]"
    :style="getSeatFrameStyle(seat)"
    :data-test="`rules-seat-node-${seat.id}`"
  >
    <div
      v-if="markers.length > 0"
      class="pointer-events-none absolute bottom-[calc(100%_-_0.25rem)] left-1/2 z-30 flex -translate-x-1/2 flex-col-reverse items-center justify-end gap-0.5"
      :aria-label="markers.map((marker) => marker.label).join(' ')"
      :title="markers.map((marker) => marker.label).join(' ')"
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
        :data-test="`rules-seat-rule-marker-${seat.id}-${marker.kind}-${marker.tone}`"
      >
        <component
          :is="markerIconByKind[marker.kind]"
          :size="12"
        />
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
