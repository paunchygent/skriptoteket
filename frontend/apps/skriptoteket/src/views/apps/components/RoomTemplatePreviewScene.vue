<script setup lang="ts">
/**
 * Room-template preview scene.
 *
 * This component renders the non-interactive preview of the current room
 * template by reusing the shared room-scene surface used by the builder.
 */

import type { RoomFixture, Seat } from "../classroomPlannerTypes";
import type { RoomGridDimensions } from "../roomFixtureLayout";
import RoomSceneSurface from "./RoomSceneSurface.vue";

defineProps<{
  roomGrid: RoomGridDimensions;
  seats: Seat[];
  fixtures: RoomFixture[];
}>();
</script>

<template>
  <details class="border border-navy bg-white p-4 shadow-brutal-sm">
    <summary class="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3">
      <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
        Förhandsvisning
      </h3>
      <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
        {{ seats.length }} sittplatser
      </span>
    </summary>

    <div class="relative mt-4 overflow-auto border border-navy/20 bg-canvas p-4">
      <RoomSceneSurface
        :grid="roomGrid"
        :seats="seats"
        :fixtures="fixtures"
        show-backdrop-grid
      />
    </div>
  </details>
</template>
