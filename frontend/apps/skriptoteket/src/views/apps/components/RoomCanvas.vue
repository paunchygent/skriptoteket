<script setup lang="ts">
/**
 * Classroom seating canvas.
 *
 * This component renders the draft room template as the seating-only canvas
 * surface with fixtures and seats. The unseated student pool now lives in the
 * seating workspace pane so the canvas can stay focused on room rendering.
 */

import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import SeatNode from "./SeatNode.vue";
import RoomFixtureArtwork from "./RoomFixtureArtwork.vue";
import type { RoomFixture } from "../classroomPlannerTypes";
import {
  getFloorFixtureFrameStyle,
  getRoomFloorLayerStyle,
  getRoomSurfaceStyle,
  getWallFixtureFrameStyle,
  normalizePresentedFixtures,
} from "../roomFixturePresentation";
import { isWallFixtureType, normalizeRoomGrid } from "../roomFixtureLayout";
import { ROOM_VIEWPORT_FRAME_PADDING } from "../roomBuilderViewport";
import { useClassroomState } from "../useClassroomState";

const props = withDefaults(defineProps<{
  selectedStudentIds?: string[];
  smartRuleMarkersByStudentId?: Record<string, string[]>;
  scalePercent: number;
  scaledSurfaceStyle: Record<string, string>;
  surfaceScale: number;
}>(), {
  selectedStudentIds: () => [],
  smartRuleMarkersByStudentId: () => ({}),
});

const emit = defineEmits<{
  (e: "viewport-size", size: { width: number; height: number }): void;
  (e: "zoom-out"): void;
  (e: "zoom-in"): void;
  (e: "zoom-fit"): void;
}>();

const state = useClassroomState();
const canvasViewport = ref<HTMLElement | null>(null);
const viewportWidth = ref(0);
const roomGrid = computed(() => normalizeRoomGrid(state.template));
const roomSurfaceStyle = computed(() => getRoomSurfaceStyle(roomGrid.value));
const roomSurfaceTransformStyle = computed(() => {
  return {
    ...roomSurfaceStyle.value,
    transform: `scale(${props.surfaceScale})`,
    transformOrigin: "top left",
  };
});
const roomFloorLayerStyle = computed(() => getRoomFloorLayerStyle(roomGrid.value));
const presentedFixtures = computed(() => normalizePresentedFixtures(state.fixtures, roomGrid.value));
const floorFixtures = computed(() => {
  return presentedFixtures.value.filter((fixture) => !isWallFixtureType(fixture.type));
});
const wallFixtures = computed(() => {
  return presentedFixtures.value.filter((fixture) => isWallFixtureType(fixture.type));
});
const shouldCenterSurface = computed(() => {
  const paddedWidth = Number.parseFloat(props.scaledSurfaceStyle.width ?? "0")
    + (ROOM_VIEWPORT_FRAME_PADDING * 2);
  return viewportWidth.value <= 0 || paddedWidth <= viewportWidth.value;
});

function floorFixtureStyle(fixture: RoomFixture): Record<string, string> {
  return getFloorFixtureFrameStyle(fixture);
}

function wallFixtureStyle(fixture: RoomFixture): Record<string, string> {
  return getWallFixtureFrameStyle(fixture, roomGrid.value);
}

function syncViewportSize(): void {
  const element = canvasViewport.value;
  if (!element) {
    emit("viewport-size", { width: 0, height: 0 });
    return;
  }

  emit("viewport-size", {
    width: element.clientWidth,
    height: element.clientHeight,
  });
  viewportWidth.value = element.clientWidth;
}

let canvasViewportObserver: ResizeObserver | null = null;

onMounted(() => {
  syncViewportSize();
  if (typeof ResizeObserver === "undefined") {
    return;
  }

  canvasViewportObserver = new ResizeObserver(() => {
    syncViewportSize();
  });

  if (canvasViewport.value) {
    canvasViewportObserver.observe(canvasViewport.value);
  }
});

onBeforeUnmount(() => {
  canvasViewportObserver?.disconnect();
  canvasViewportObserver = null;
});
</script>

<template>
  <section class="border border-navy bg-white p-3 shadow-brutal-sm">
    <div class="flex flex-col gap-2 border-b border-navy/20 pb-2 md:flex-row md:items-start md:justify-between">
      <div>
        <h3 class="font-serif text-lg text-navy">
          Sittschema
        </h3>
        <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
          Dra elever till en plats eller byt två elevers placering genom att släppa ovanpå en upptagen stol.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span
          data-test="seating-zoom-percent"
          class="border border-navy/20 bg-white px-2 py-1 text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60"
        >
          {{ scalePercent }}%
        </span>
        <button
          type="button"
          data-test="seating-zoom-out"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          @click="emit('zoom-out')"
        >
          −
        </button>
        <button
          type="button"
          data-test="seating-zoom-in"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          @click="emit('zoom-in')"
        >
          +
        </button>
        <button
          type="button"
          data-test="seating-zoom-fit"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          @click="emit('zoom-fit')"
        >
          Anpassa
        </button>
      </div>
    </div>

    <div
      ref="canvasViewport"
      data-test="room-canvas-viewport"
      class="mt-3 min-h-[480px] overflow-auto border border-navy/20 bg-white p-3"
    >
      <div
        data-test="room-canvas-scroll-frame"
        :data-overflow-anchor="shouldCenterSurface ? 'center' : 'start'"
        class="flex min-h-full min-w-full items-start"
        :class="shouldCenterSurface ? 'justify-center' : 'justify-start'"
      >
        <div
          class="shrink-0 px-6 py-6"
          data-test="room-canvas-surface-shell"
        >
          <div
            class="relative"
            :style="scaledSurfaceStyle"
          >
            <div
              class="absolute left-0 top-0 room-canvas-surface"
              :style="roomSurfaceTransformStyle"
            >
              <div
                class="absolute inset-0 border border-navy/40 bg-white"
              />

              <div
                class="absolute"
                :style="roomFloorLayerStyle"
              >
                <div class="absolute inset-0 border border-navy bg-white" />
                <div
                  class="absolute inset-0 room-canvas-grid opacity-15"
                />

                <div
                  v-for="fixture in floorFixtures"
                  :key="fixture.id"
                  class="absolute overflow-visible"
                  :style="floorFixtureStyle(fixture)"
                >
                  <RoomFixtureArtwork
                    :fixture="fixture"
                    :fixtures="presentedFixtures"
                    :grid="roomGrid"
                  />
                </div>

                <SeatNode
                  v-for="seat in state.seats"
                  :key="seat.id"
                  :seat="seat"
                  :student="state.studentBySeatId[seat.id]"
                  :markers="props.smartRuleMarkersByStudentId[state.studentBySeatId[seat.id]?.id ?? ''] ?? []"
                  :selected="props.selectedStudentIds.includes(state.studentBySeatId[seat.id]?.id ?? '')"
                  @student-dropped="state.assignStudentToSeat"
                  @student-removed="state.clearSeatAssignment"
                  @swap-requested="state.swapSeatAssignments"
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
                  :fixtures="presentedFixtures"
                  :grid="roomGrid"
                />
              </div>
            </div>
          </div>
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
