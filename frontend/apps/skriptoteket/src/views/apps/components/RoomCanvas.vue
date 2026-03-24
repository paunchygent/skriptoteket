<script setup lang="ts">
/**
 * Classroom seating canvas.
 *
 * This component renders the draft room template as the seating-only canvas
 * surface with fixtures and seats. The unseated student pool now lives in the
 * seating workspace pane so the canvas can stay focused on room rendering.
 */

import { computed } from "vue";

import SeatNode from "./SeatNode.vue";
import RoomFixtureArtwork from "./RoomFixtureArtwork.vue";
import type { RoomFixture } from "../classroomPlannerTypes";
import {
  getFloorFixtureFrameStyle,
  getRoomFloorLayerStyle,
  getRoomSurfaceStyle,
  getWallFixtureFrameStyle,
} from "../roomFixturePresentation";
import { isWallFixtureType, normalizeRoomGrid } from "../roomFixtureLayout";
import { useClassroomState } from "../useClassroomState";

const props = defineProps<{
  selectedStudentId?: string | null;
}>();

const emit = defineEmits<{
  (e: "student-selected", studentId: string): void;
}>();

const state = useClassroomState();
const roomGrid = computed(() => normalizeRoomGrid(state.template));
const roomSurfaceStyle = computed(() => getRoomSurfaceStyle(roomGrid.value));
const roomFloorLayerStyle = computed(() => getRoomFloorLayerStyle(roomGrid.value));
const floorFixtures = computed(() => {
  return state.fixtures.filter((fixture) => !isWallFixtureType(fixture.type));
});
const wallFixtures = computed(() => {
  return state.fixtures.filter((fixture) => isWallFixtureType(fixture.type));
});

function floorFixtureStyle(fixture: RoomFixture): Record<string, string> {
  return getFloorFixtureFrameStyle(fixture);
}

function wallFixtureStyle(fixture: RoomFixture): Record<string, string> {
  return getWallFixtureFrameStyle(fixture, roomGrid.value);
}
</script>

<template>
  <section class="border border-navy bg-white p-4 shadow-brutal-sm">
    <div class="flex flex-col gap-3 border-b border-navy/20 pb-3 md:flex-row md:items-end md:justify-between">
      <h3 class="font-serif text-xl text-navy">
        Sittschema
      </h3>
      <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
        Dra elever till en plats eller byt två elevers placering genom att släppa ovanpå en upptagen stol.
      </p>
    </div>

    <div class="mt-4 overflow-auto border border-navy/20 bg-canvas p-4">
      <div
        class="relative room-canvas-surface"
        :style="roomSurfaceStyle"
      >
        <div
          class="absolute room-canvas-grid opacity-15"
          :style="roomFloorLayerStyle"
        />

        <div
          class="absolute"
          :style="roomFloorLayerStyle"
        >
          <div
            v-for="fixture in floorFixtures"
            :key="fixture.id"
            class="absolute overflow-visible"
            :style="floorFixtureStyle(fixture)"
          >
            <RoomFixtureArtwork
              :fixture="fixture"
              :fixtures="state.fixtures"
              :grid="roomGrid"
            />
          </div>

          <SeatNode
            v-for="seat in state.seats"
            :key="seat.id"
            :seat="seat"
            :student="state.studentBySeatId[seat.id]"
            :selected="props.selectedStudentId === state.studentBySeatId[seat.id]?.id"
            @student-dropped="state.assignStudentToSeat"
            @student-removed="state.clearSeatAssignment"
            @swap-requested="state.swapSeatAssignments"
            @student-selected="emit('student-selected', $event)"
          />
        </div>

        <div
          v-for="fixture in wallFixtures"
          :key="fixture.id"
          class="absolute overflow-visible"
          :style="wallFixtureStyle(fixture)"
        >
          <RoomFixtureArtwork
            :fixture="fixture"
            :fixtures="state.fixtures"
            :grid="roomGrid"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.room-canvas-surface {
  --planner-grid-size: 24px;
}

.room-canvas-grid {
  background-image:
    linear-gradient(var(--huleedu-navy) 1px, transparent 1px),
    linear-gradient(90deg, var(--huleedu-navy) 1px, transparent 1px);
  background-size: var(--planner-grid-size) var(--planner-grid-size);
}
</style>
