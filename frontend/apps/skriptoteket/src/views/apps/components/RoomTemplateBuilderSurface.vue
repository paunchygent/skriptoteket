<script setup lang="ts">
/**
 * Room-template builder surface.
 *
 * This component renders the interactive room grid, zoom controls, and ghost
 * overlays while delegating editor state to the extracted composable.
 */

import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { getRoomSurfaceStyle, getWallFixtureFrameStyle } from "../roomFixturePresentation";
import { getSeatGhostFrameStyle } from "../roomSeatPresentation";
import {
  ROOM_GRID_UNIT,
  isWallFixtureType,
  type RoomGridDimensions,
} from "../roomFixtureLayout";
import type { RoomTemplateGhostPlacement } from "../useRoomTemplateEditorState";
import type { RoomFixture, Seat } from "../classroomPlannerTypes";
import RoomFixtureArtwork from "./RoomFixtureArtwork.vue";
import RoomSceneSurface from "./RoomSceneSurface.vue";
import RoomSeatToken from "./RoomSeatToken.vue";

const props = defineProps<{
  roomGrid: RoomGridDimensions;
  seats: Seat[];
  fixtures: RoomFixture[];
  ghostPlacement: RoomTemplateGhostPlacement | null;
  ghostRenderableFixture: RoomFixture | null;
  builderScale: number;
  builderScaledSurfaceStyle: Record<string, string>;
  builderScalePercent: number;
}>();

const emit = defineEmits<{
  (e: "zoom-out"): void;
  (e: "zoom-in"): void;
  (e: "zoom-fit"): void;
  (e: "clear-hover"): void;
  (e: "cell-hover", event: MouseEvent, row: number, col: number): void;
  (e: "cell-focus", row: number, col: number): void;
  (e: "cell-click", row: number, col: number, event: MouseEvent): void;
  (e: "viewport-size", size: { width: number; height: number }): void;
}>();

const builderViewport = ref<HTMLElement | null>(null);
const viewportWidth = ref(0);

function ghostPlacementClass(canPlace: boolean, type: RoomTemplateGhostPlacement["type"]): string {
  if (!canPlace) {
    return "border-burgundy bg-burgundy/10 text-burgundy opacity-70";
  }
  if (type === "seat") {
    return "border-navy/70 bg-navy/10";
  }
  return "border-navy/40 bg-white/40";
}

function syncBuilderViewportSize(): void {
  const element = builderViewport.value;
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

let builderViewportObserver: ResizeObserver | null = null;

onMounted(() => {
  syncBuilderViewportSize();
  if (typeof ResizeObserver === "undefined") {
    return;
  }

  builderViewportObserver = new ResizeObserver(() => {
    syncBuilderViewportSize();
  });

  if (builderViewport.value) {
    builderViewportObserver.observe(builderViewport.value);
  }
});

onBeforeUnmount(() => {
  builderViewportObserver?.disconnect();
  builderViewportObserver = null;
});

const showFloorGhost = computed(() => {
  return (
    props.ghostPlacement
    && (!props.ghostRenderableFixture || props.ghostPlacement.type === "seat" || !isWallFixtureType(props.ghostPlacement.type))
  );
});

const showWallGhost = computed(() => {
  return (
    props.ghostPlacement
    && props.ghostPlacement.type !== "seat"
    && props.ghostRenderableFixture
    && isWallFixtureType(props.ghostPlacement.type)
  );
});

const builderSurfaceTransformStyle = computed(() => {
  return {
    ...getRoomSurfaceStyle(props.roomGrid),
    transform: `scale(${props.builderScale})`,
    transformOrigin: "top left",
  };
});
const shouldCenterSurface = computed(() => {
  const scaledWidth = Number.parseFloat(props.builderScaledSurfaceStyle.width ?? "0");
  return viewportWidth.value <= 0 || scaledWidth <= viewportWidth.value;
});
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col border border-navy bg-canvas p-4 shadow-brutal-sm">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
          Klassrumsyta
        </h3>
        <p class="text-xs text-navy/60">
          Anpassa vyn utan att ändra klassrummets sparade geometri.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span
          data-test="builder-zoom-percent"
          class="border border-navy/20 bg-white px-2 py-1 text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60"
        >
          {{ builderScalePercent }}%
        </span>
        <button
          type="button"
          data-test="builder-zoom-out"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          @click="emit('zoom-out')"
        >
          −
        </button>
        <button
          type="button"
          data-test="builder-zoom-in"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          @click="emit('zoom-in')"
        >
          +
        </button>
        <button
          type="button"
          data-test="builder-zoom-fit"
          class="btn-ghost planner-btn-ghost planner-btn-ghost-compact"
          @click="emit('zoom-fit')"
        >
          Anpassa
        </button>
      </div>
    </div>

    <div
      ref="builderViewport"
      data-test="room-builder-viewport"
      class="min-h-[560px] flex-1 overflow-auto border border-navy/20 bg-white/70 p-3 lg:min-h-[640px]"
    >
      <div
        data-test="room-builder-scroll-frame"
        :data-overflow-anchor="shouldCenterSurface ? 'center' : 'start'"
        class="flex min-h-full min-w-full items-start"
        :class="shouldCenterSurface ? 'justify-center' : 'justify-start'"
      >
        <div
          class="relative shrink-0"
          :style="builderScaledSurfaceStyle"
        >
          <div
            class="absolute left-0 top-0"
            :style="builderSurfaceTransformStyle"
            @mouseleave="emit('clear-hover')"
          >
            <RoomSceneSurface
              :grid="roomGrid"
              :seats="seats"
              :fixtures="fixtures"
              :normalize-presentation="false"
              fixture-surface="builder-grid"
            >
              <template #floor-base>
                <div
                  class="relative grid h-full w-full gap-1"
                  :style="{ gridTemplateColumns: `repeat(${roomGrid.cols}, minmax(0, 1fr))` }"
                >
                  <template
                    v-for="row in roomGrid.rows"
                    :key="`row-${row}`"
                  >
                    <button
                      v-for="col in roomGrid.cols"
                      :key="`cell-${row}-${col}`"
                      type="button"
                      class="planner-grid-node-button"
                      @mousemove="emit('cell-hover', $event, row - 1, col - 1)"
                      @focus="emit('cell-focus', row - 1, col - 1)"
                      @click="emit('cell-click', row - 1, col - 1, $event)"
                    />
                  </template>
                </div>
              </template>

              <template #floor-overlay>
                <div
                  v-if="showFloorGhost"
                  class="pointer-events-none absolute inset-0 z-20"
                >
                  <div
                    v-if="ghostPlacement?.type === 'seat'"
                    class="absolute"
                    :style="getSeatGhostFrameStyle(ghostPlacement.row, ghostPlacement.col)"
                  >
                    <RoomSeatToken
                      :seat-id="`seat-${ghostPlacement.row + 1}-${ghostPlacement.col + 1}`"
                      ghost
                    />
                  </div>
                  <div
                    v-else-if="ghostRenderableFixture && ghostPlacement"
                    class="absolute rounded-sm border-2 border-dashed"
                    :class="ghostPlacementClass(ghostPlacement.canPlace, ghostPlacement.type)"
                    :style="{
                      left: `${ghostPlacement.col * ROOM_GRID_UNIT}px`,
                      top: `${ghostPlacement.row * ROOM_GRID_UNIT}px`,
                      width: `${ghostPlacement.width * ROOM_GRID_UNIT}px`,
                      height: `${ghostPlacement.height * ROOM_GRID_UNIT}px`,
                    }"
                  >
                    <RoomFixtureArtwork
                      :fixture="ghostRenderableFixture"
                      :grid="roomGrid"
                      surface="ghost"
                    />
                  </div>
                </div>
              </template>

              <template #wall-overlay>
                <div
                  v-if="showWallGhost && ghostRenderableFixture && ghostPlacement"
                  class="pointer-events-none absolute inset-0 z-20"
                >
                  <div
                    class="absolute rounded-sm border-2 border-dashed"
                    :class="ghostPlacementClass(ghostPlacement.canPlace, ghostPlacement.type)"
                    :style="getWallFixtureFrameStyle(ghostRenderableFixture, roomGrid)"
                  >
                    <RoomFixtureArtwork
                      :fixture="ghostRenderableFixture"
                      :grid="roomGrid"
                      surface="ghost"
                    />
                  </div>
                </div>
              </template>
            </RoomSceneSurface>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
