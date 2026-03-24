<script setup lang="ts">
/**
 * Shared room-scene surface.
 *
 * This component renders the saved room scene layers shared by the template
 * builder and the preview surface so both views rely on one floor/wall/seat
 * composition model.
 */

import { computed, useSlots } from "vue";

import type { RoomFixture, Seat } from "../classroomPlannerTypes";
import {
  getFloorFixtureFrameStyle,
  getRoomFloorLayerStyle,
  getRoomSurfaceStyle,
  getWallFixtureFrameStyle,
  normalizeRoomFixtureAnnotations,
  normalizePresentedFixtures,
  type PresentedRoomFixture,
} from "../roomFixturePresentation";
import { getSeatFrameStyle } from "../roomSeatPresentation";
import { isWallFixtureType, type RoomGridDimensions } from "../roomFixtureLayout";
import RoomFixtureArtwork from "./RoomFixtureArtwork.vue";
import RoomSeatToken from "./RoomSeatToken.vue";

const props = withDefaults(defineProps<{
  grid: RoomGridDimensions;
  seats: Seat[];
  fixtures: RoomFixture[];
  normalizePresentation?: boolean;
  showBackdropGrid?: boolean;
  fixtureSurface?: "absolute" | "builder-grid" | "ghost";
}>(), {
  normalizePresentation: true,
  showBackdropGrid: false,
  fixtureSurface: "absolute",
});

const slots = useSlots();

const roomSurfaceStyle = computed(() => getRoomSurfaceStyle(props.grid));
const roomFloorLayerStyle = computed(() => getRoomFloorLayerStyle(props.grid));
const renderedFixtures = computed<PresentedRoomFixture[]>(() => {
  return props.normalizePresentation
    ? normalizePresentedFixtures(props.fixtures, props.grid)
    : normalizeRoomFixtureAnnotations(props.fixtures, props.grid);
});
const floorFixtures = computed(() => {
  return renderedFixtures.value.filter((fixture) => !isWallFixtureType(fixture.type));
});
const wallFixtures = computed(() => {
  return renderedFixtures.value.filter((fixture) => isWallFixtureType(fixture.type));
});
const hasFloorBase = computed(() => Boolean(slots["floor-base"]));
const hasFloorOverlay = computed(() => Boolean(slots["floor-overlay"]));
const hasWallOverlay = computed(() => Boolean(slots["wall-overlay"]));
</script>

<template>
  <div
    class="relative"
    :style="roomSurfaceStyle"
  >
    <div class="absolute inset-0 border border-navy/40 bg-white" />

    <div
      class="absolute"
      :style="roomFloorLayerStyle"
    >
      <div class="relative h-full w-full">
        <div class="absolute inset-0 border border-navy bg-white" />

        <div
          v-if="showBackdropGrid"
          class="absolute inset-0 opacity-15"
          :style="{
            backgroundImage: 'linear-gradient(var(--huleedu-navy) 1px, transparent 1px), linear-gradient(90deg, var(--huleedu-navy) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }"
        />

        <slot
          v-if="hasFloorBase"
          name="floor-base"
        />

        <div class="pointer-events-none absolute inset-0 z-10">
          <div
            v-for="fixture in floorFixtures"
            :key="fixture.id"
            class="absolute overflow-visible"
            :style="getFloorFixtureFrameStyle(fixture)"
          >
            <RoomFixtureArtwork
              :fixture="fixture"
              :fixtures="renderedFixtures"
              :grid="grid"
              :surface="fixtureSurface"
            />
          </div>

          <div
            v-for="seat in seats"
            :key="seat.id"
            class="absolute"
            :style="getSeatFrameStyle(seat)"
          >
            <RoomSeatToken :seat-id="seat.id" />
          </div>
        </div>

        <slot
          v-if="hasFloorOverlay"
          name="floor-overlay"
        />
      </div>
    </div>

    <div class="pointer-events-none absolute inset-0 z-10">
      <div
        v-for="fixture in wallFixtures"
        :key="fixture.id"
        class="absolute overflow-visible"
        :style="getWallFixtureFrameStyle(fixture, grid)"
      >
        <RoomFixtureArtwork
          :fixture="fixture"
          :fixtures="renderedFixtures"
          :grid="grid"
          :surface="fixtureSurface"
        />
      </div>
    </div>

    <slot
      v-if="hasWallOverlay"
      name="wall-overlay"
    />
  </div>
</template>
