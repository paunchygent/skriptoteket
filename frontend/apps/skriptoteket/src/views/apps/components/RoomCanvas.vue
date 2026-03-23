<script setup lang="ts">
/**
 * Classroom seating canvas.
 *
 * This component renders the draft room template as a whiteboard-style
 * classroom scene with fixtures, seats, and an unseated student pool. It keeps
 * the drag-and-drop surface visually rich for later export stories while
 * routing all state mutations through the planner store.
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

function onDragStart(event: DragEvent, studentId: string): void {
  if (event.dataTransfer) {
    event.dataTransfer.setData("studentId", studentId);
    event.dataTransfer.effectAllowed = "move";
  }
}

function onDropToPool(event: DragEvent): void {
  event.preventDefault();
  const studentId = event.dataTransfer?.getData("studentId");
  if (studentId) {
    state.clearSeatAssignment(studentId);
  }
}

function onDragOver(event: DragEvent): void {
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
}

function floorFixtureStyle(fixture: RoomFixture): Record<string, string> {
  return getFloorFixtureFrameStyle(fixture);
}

function wallFixtureStyle(fixture: RoomFixture): Record<string, string> {
  return getWallFixtureFrameStyle(fixture, roomGrid.value);
}
</script>

<template>
  <div class="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
    <aside
      class="flex min-h-[320px] flex-col border border-navy bg-white p-4 shadow-brutal-sm"
      @dragover="onDragOver"
      @drop="onDropToPool"
    >
      <div class="flex items-end justify-between gap-3 border-b border-navy/20 pb-3">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Placering
          </p>
          <h3 class="font-serif text-xl text-navy">
            Ej placerade
          </h3>
        </div>
        <span class="border border-navy bg-canvas px-2 py-1 text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/70">
          {{ state.unseatedStudents.length }}
        </span>
      </div>

      <div class="mt-4 flex flex-1 flex-col gap-2 overflow-y-auto">
        <button
          v-for="student in state.unseatedStudents"
          :key="student.id"
          type="button"
          class="flex items-start justify-between gap-3 border px-3 py-2 text-left transition-colors"
          :class="props.selectedStudentId === student.id ? 'border-burgundy bg-burgundy/10 text-burgundy' : 'border-navy bg-white text-navy hover:bg-canvas'"
          draggable="true"
          @click="emit('student-selected', student.id)"
          @dragstart="onDragStart($event, student.id)"
        >
          <div class="min-w-0">
            <div class="truncate text-sm font-semibold">
              {{ student.display_name }}
            </div>
          </div>
        </button>

        <div
          v-if="state.unseatedStudents.length === 0"
          class="flex flex-1 items-center justify-center border border-dashed border-navy/30 bg-canvas px-4 py-6 text-center text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/40"
        >
          Alla elever har fått plats
        </div>
      </div>
    </aside>

    <section class="border border-navy bg-white p-4 shadow-brutal-sm">
      <div class="flex flex-col gap-3 border-b border-navy/20 pb-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
            Klassrumsyta
          </p>
          <h3 class="font-serif text-xl text-navy">
            Sittschema
          </h3>
        </div>
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
  </div>
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
