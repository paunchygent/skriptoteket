<script setup lang="ts">
/**
 * Room template create/edit modal.
 *
 * This modal manages reusable classroom layouts for the planner. It lets the
 * teacher place seats and room objects on a configurable grid so the live
 * seating canvas, future exports, and classroom snapshots share one saved room
 * contract.
 */

import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import { apiDelete, apiPost, apiPut } from "../../../api/client";
import RoomFixtureArtwork from "./RoomFixtureArtwork.vue";
import RoomSeatToken from "./RoomSeatToken.vue";
import {
  type RoomFixture,
  type RoomFixtureType,
  type RoomTemplate,
  type Seat,
} from "../classroomPlannerTypes";
import {
  buildRoomFixtureLabel,
  fixtureContainsCell,
  getRoomFixturePaletteEntry,
  isFloorFixtureType,
  isWallFixtureType,
  MIN_ROOM_GRID_COLS,
  MIN_ROOM_GRID_ROWS,
  normalizeFixturePlacement,
  normalizeRoomGrid,
  rectanglesOverlap,
  resolveWallSideForPointer,
  roomFixturePalette,
  ROOM_GRID_UNIT,
  type PointerAnchor,
  type RoomGridDimensions,
  type WallSide,
} from "../roomFixtureLayout";
import {
  buildRoomFixtureFromGridPlacement,
  getFloorFixtureFrameStyle,
  getFloorPlacementStyle,
  getRoomFloorLayerStyle,
  getRoomSurfaceMetrics,
  getRoomSurfaceStyle,
  getWallFixtureFrameStyle,
} from "../roomFixturePresentation";
import {
  clampRoomViewportScale,
  computeRoomViewportFitScale,
  getScaledRoomSurfaceStyle,
  ROOM_VIEWPORT_SCALE_STEP,
} from "../roomBuilderViewport";
import { getSeatFrameStyle, getSeatGhostFrameStyle } from "../roomSeatPresentation";

type BuilderTool = "seat" | "erase" | RoomFixtureType;

type FixturePlacement = {
  id: string;
  type: RoomFixtureType;
  col: number;
  row: number;
  width: number;
  height: number;
  label: string | null;
};

type HoveredCell = {
  row: number;
  col: number;
};

const props = defineProps<{
  template?: RoomTemplate | null;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "saved", template: RoomTemplate): void;
  (e: "deleted", templateId: string): void;
}>();

const name = ref("");
const selectedTool = ref<BuilderTool>("seat");
const seatCells = ref<string[]>([]);
const fixtures = ref<FixturePlacement[]>([]);
const gridCols = ref(MIN_ROOM_GRID_COLS);
const gridRows = ref(MIN_ROOM_GRID_ROWS);
const hoveredCell = ref<HoveredCell | null>(null);
const pointerAnchor = ref<PointerAnchor | null>(null);
const isSubmitting = ref(false);
const isDeleting = ref(false);
const error = ref<string | null>(null);
const builderViewport = ref<HTMLElement | null>(null);
const builderViewportSize = ref({ width: 0, height: 0 });
const manualZoomScale = ref<number | null>(null);

const isEditing = computed(() => Boolean(props.template));
const roomGrid = computed<RoomGridDimensions>(() => normalizeRoomGrid({
  cols: gridCols.value,
  rows: gridRows.value,
}));
const roomSurfaceStyle = computed(() => getRoomSurfaceStyle(roomGrid.value));
const roomFloorLayerStyle = computed(() => getRoomFloorLayerStyle(roomGrid.value));
const roomSurfaceMetrics = computed(() => getRoomSurfaceMetrics(roomGrid.value));
const builderFitScale = computed(() => {
  return computeRoomViewportFitScale(builderViewportSize.value, roomSurfaceMetrics.value);
});
const builderScale = computed(() => manualZoomScale.value ?? builderFitScale.value);
const builderScaledSurfaceStyle = computed(() => {
  return getScaledRoomSurfaceStyle(roomSurfaceMetrics.value, builderScale.value);
});
const builderSurfaceTransformStyle = computed(() => {
  return {
    ...roomSurfaceStyle.value,
    transform: `scale(${builderScale.value})`,
    transformOrigin: "top left",
  };
});
const builderScalePercent = computed(() => Math.round(builderScale.value * 100));

function seatKey(row: number, col: number): string {
  return `${row}:${col}`;
}

function isSeatAt(row: number, col: number): boolean {
  return seatCells.value.includes(seatKey(row, col));
}

function findFloorFixtureAt(row: number, col: number): FixturePlacement | null {
  return (
    fixtures.value.find((fixture) => {
      return isFloorFixtureType(fixture.type) && fixtureContainsCell(fixture, row, col);
    }) ?? null
  );
}

function findWallFixtureAt(row: number, col: number): FixturePlacement | null {
  return (
    fixtures.value.find((fixture) => {
      return isWallFixtureType(fixture.type) && fixtureContainsCell(fixture, row, col);
    }) ?? null
  );
}

function fixtureFits(
  type: RoomFixtureType,
  row: number,
  col: number,
  wallSideOverride?: WallSide | null,
): boolean {
  const placement = normalizeFixturePlacement(type, row, col, roomGrid.value, wallSideOverride);
  if (!placement) {
    return false;
  }

  if (isWallFixtureType(type)) {
    return !fixtures.value.some((fixture) => {
      return isWallFixtureType(fixture.type) && rectanglesOverlap(placement, fixture);
    });
  }

  for (let currentRow = placement.row; currentRow < placement.row + placement.height; currentRow += 1) {
    for (let currentCol = placement.col; currentCol < placement.col + placement.width; currentCol += 1) {
      if (isSeatAt(currentRow, currentCol) || findFloorFixtureAt(currentRow, currentCol)) {
        return false;
      }
    }
  }
  return true;
}

function removeFixtureById(fixtureId: string): void {
  fixtures.value = fixtures.value.filter((fixture) => fixture.id !== fixtureId);
}

function updateHoverState(event: MouseEvent, row: number, col: number): void {
  hoveredCell.value = { row, col };
  const target = event.currentTarget;
  if (!(target instanceof HTMLElement)) {
    return;
  }

  const rect = target.getBoundingClientRect();
  const relativeX = rect.width === 0 ? 0.5 : (event.clientX - rect.left) / rect.width;
  const relativeY = rect.height === 0 ? 0.5 : (event.clientY - rect.top) / rect.height;
  pointerAnchor.value = {
    x: col * ROOM_GRID_UNIT + (relativeX * ROOM_GRID_UNIT),
    y: row * ROOM_GRID_UNIT + (relativeY * ROOM_GRID_UNIT),
    relativeX,
    relativeY,
  };
}

function clearHoverState(): void {
  hoveredCell.value = null;
  pointerAnchor.value = null;
}

function currentWallSide(): WallSide | null {
  if (!pointerAnchor.value || !hoveredCell.value) {
    return null;
  }
  return resolveWallSideForPointer(
    pointerAnchor.value,
    hoveredCell.value.row,
    hoveredCell.value.col,
    roomGrid.value,
  );
}

function resolveWallSideForPlacement(event: MouseEvent | undefined, row: number, col: number): WallSide | null {
  const target = event?.currentTarget;
  if (!(target instanceof HTMLElement)) {
    return currentWallSide();
  }

  const rect = target.getBoundingClientRect();
  const clientX = event?.clientX ?? (rect.left + (rect.width / 2));
  const clientY = event?.clientY ?? (rect.top + (rect.height / 2));
  const relativeX = rect.width === 0 ? 0.5 : (clientX - rect.left) / rect.width;
  const relativeY = rect.height === 0 ? 0.5 : (clientY - rect.top) / rect.height;
  return resolveWallSideForPointer(
    {
      x: col * ROOM_GRID_UNIT + (relativeX * ROOM_GRID_UNIT),
      y: row * ROOM_GRID_UNIT + (relativeY * ROOM_GRID_UNIT),
      relativeX,
      relativeY,
    },
    row,
    col,
    roomGrid.value,
  );
}

function toggleGridCell(row: number, col: number, event?: MouseEvent): void {
  error.value = null;
  if (event) {
    updateHoverState(event, row, col);
  }

  const occupiedFloorFixture = findFloorFixtureAt(row, col);
  const occupiedWallFixture = findWallFixtureAt(row, col);

  if (selectedTool.value === "erase") {
    if (occupiedWallFixture) {
      removeFixtureById(occupiedWallFixture.id);
      return;
    }
    if (occupiedFloorFixture) {
      removeFixtureById(occupiedFloorFixture.id);
      return;
    }
    seatCells.value = seatCells.value.filter((value) => value !== seatKey(row, col));
    return;
  }

  if (selectedTool.value === "seat") {
    if (occupiedFloorFixture) {
      error.value = "Ta bort möbeln eller objektet först om du vill lägga en plats där.";
      return;
    }
    const key = seatKey(row, col);
    seatCells.value = isSeatAt(row, col)
      ? seatCells.value.filter((value) => value !== key)
      : [...seatCells.value, key];
    return;
  }

  const paletteItem = getRoomFixturePaletteEntry(selectedTool.value);
  if (!paletteItem) {
    return;
  }
  const wallSide = isWallFixtureType(selectedTool.value)
    ? resolveWallSideForPlacement(event, row, col)
    : null;
  const placement = normalizeFixturePlacement(selectedTool.value, row, col, roomGrid.value, wallSide);
  if (!placement || !fixtureFits(selectedTool.value, row, col, wallSide)) {
    error.value = isWallFixtureType(selectedTool.value)
      ? "Det valda objektet måste få plats längs väggen utan att krocka med andra väggobjekt."
      : "Det valda objektet får inte plats där eller krockar med befintlig möblering.";
    return;
  }

  fixtures.value = [
    ...fixtures.value,
    {
      id: `${selectedTool.value}-${crypto.randomUUID().slice(0, 8)}`,
      type: selectedTool.value,
      row: placement.row,
      col: placement.col,
      width: placement.width,
      height: placement.height,
      label: buildRoomFixtureLabel(selectedTool.value),
    },
  ];
}

function templateFitsGrid(cols: number, rows: number): boolean {
  const allSeatsFit = seatCells.value.every((value) => {
    const [row, col] = value.split(":").map(Number);
    return row < rows && col < cols;
  });
  if (!allSeatsFit) {
    return false;
  }
  return fixtures.value.every((fixture) => {
    return fixture.row + fixture.height <= rows && fixture.col + fixture.width <= cols;
  });
}

const canShrinkCols = computed(() => {
  return gridCols.value > MIN_ROOM_GRID_COLS && templateFitsGrid(gridCols.value - 1, gridRows.value);
});

const canShrinkRows = computed(() => {
  return gridRows.value > MIN_ROOM_GRID_ROWS && templateFitsGrid(gridCols.value, gridRows.value - 1);
});

function resizeRoom(axis: "cols" | "rows", delta: 1 | -1): void {
  error.value = null;
  if (axis === "cols") {
    if (delta < 0 && !canShrinkCols.value) {
      error.value = "Ta bort eller flytta objekt längst ut till höger innan du gör klassrummet smalare.";
      return;
    }
    gridCols.value = Math.max(MIN_ROOM_GRID_COLS, gridCols.value + delta);
    return;
  }

  if (delta < 0 && !canShrinkRows.value) {
    error.value = "Ta bort eller flytta objekt längst ned innan du gör klassrummet lägre.";
    return;
  }
  gridRows.value = Math.max(MIN_ROOM_GRID_ROWS, gridRows.value + delta);
}

let builderViewportObserver: ResizeObserver | null = null;

function syncBuilderViewportSize(): void {
  const element = builderViewport.value;
  if (!element) {
    builderViewportSize.value = { width: 0, height: 0 };
    return;
  }

  builderViewportSize.value = {
    width: element.clientWidth,
    height: element.clientHeight,
  };
}

function zoomOut(): void {
  const currentScale = manualZoomScale.value ?? builderFitScale.value;
  manualZoomScale.value = clampRoomViewportScale(currentScale - ROOM_VIEWPORT_SCALE_STEP);
}

function zoomIn(): void {
  const currentScale = manualZoomScale.value ?? builderFitScale.value;
  manualZoomScale.value = clampRoomViewportScale(currentScale + ROOM_VIEWPORT_SCALE_STEP);
}

function resetBuilderZoom(): void {
  manualZoomScale.value = null;
}

function clearRoomContents(): void {
  seatCells.value = [];
  fixtures.value = [];
  selectedTool.value = "seat";
  hoveredCell.value = null;
  pointerAnchor.value = null;
  error.value = null;
}

watch(
  () => props.template,
  (template) => {
    const normalizedGrid = normalizeRoomGrid(template);
    name.value = template?.name ?? "";
    gridCols.value = normalizedGrid.cols;
    gridRows.value = normalizedGrid.rows;
    seatCells.value =
      template?.seats.map((seat) => seatKey(Math.round(seat.y / ROOM_GRID_UNIT), Math.round(seat.x / ROOM_GRID_UNIT))) ??
      [];
    fixtures.value =
      template?.fixtures.map((fixture) => ({
        id: fixture.id,
        type: fixture.type,
        row: Math.round(fixture.y / ROOM_GRID_UNIT),
        col: Math.round(fixture.x / ROOM_GRID_UNIT),
        width: Math.max(1, Math.round(fixture.width / ROOM_GRID_UNIT)),
        height: Math.max(1, Math.round(fixture.height / ROOM_GRID_UNIT)),
        label: fixture.label ?? buildRoomFixtureLabel(fixture.type),
      })) ?? [];
    hoveredCell.value = null;
    pointerAnchor.value = null;
    error.value = null;
    selectedTool.value = "seat";
    manualZoomScale.value = null;
  },
  { immediate: true },
);

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

const ghostPlacement = computed(() => {
  if (!hoveredCell.value || selectedTool.value === "erase") {
    return null;
  }

  if (selectedTool.value === "seat") {
    return {
      row: hoveredCell.value.row,
      col: hoveredCell.value.col,
      width: 1,
      height: 1,
      wallSide: null,
      type: "seat" as const,
      canPlace: !findFloorFixtureAt(hoveredCell.value.row, hoveredCell.value.col),
    };
  }

  const wallSide = isWallFixtureType(selectedTool.value) ? currentWallSide() : null;
  const placement = normalizeFixturePlacement(
    selectedTool.value,
    hoveredCell.value.row,
    hoveredCell.value.col,
    roomGrid.value,
    wallSide,
  );
  if (!placement) {
    return null;
  }

  return {
    ...placement,
    type: selectedTool.value,
    canPlace: fixtureFits(selectedTool.value, hoveredCell.value.row, hoveredCell.value.col, wallSide),
  };
});

const parsedSeats = computed<Seat[]>(() => {
  return seatCells.value
    .map((value) => {
      const [row, col] = value.split(":").map(Number);
      return { row, col };
    })
    .sort((left, right) => (left.row - right.row) || (left.col - right.col))
    .map((cell, index) => ({
      id: `seat-${index + 1}`,
      x: cell.col * ROOM_GRID_UNIT,
      y: cell.row * ROOM_GRID_UNIT,
      zone: null,
    }));
});

const parsedFixtures = computed<RoomFixture[]>(() => {
  return fixtures.value.map((fixture) => ({
    id: fixture.id,
    type: fixture.type,
    x: fixture.col * ROOM_GRID_UNIT,
    y: fixture.row * ROOM_GRID_UNIT,
    width: fixture.width * ROOM_GRID_UNIT,
    height: fixture.height * ROOM_GRID_UNIT,
    label: fixture.label,
  }));
});

const builderRenderableFixtures = computed(() => {
  return fixtures.value.map((fixture) => ({
    placement: fixture,
    pixelFixture: buildRoomFixtureFromGridPlacement(fixture),
  }));
});

const builderFloorFixtures = computed(() => {
  return builderRenderableFixtures.value.filter((fixture) => !isWallFixtureType(fixture.placement.type));
});

const builderWallFixtures = computed(() => {
  return builderRenderableFixtures.value.filter((fixture) => isWallFixtureType(fixture.placement.type));
});

const ghostRenderableFixture = computed<RoomFixture | null>(() => {
  if (!ghostPlacement.value || ghostPlacement.value.type === "seat") {
    return null;
  }

  return {
    id: `ghost-${ghostPlacement.value.type}`,
    type: ghostPlacement.value.type,
    x: ghostPlacement.value.col * ROOM_GRID_UNIT,
    y: ghostPlacement.value.row * ROOM_GRID_UNIT,
    width: ghostPlacement.value.width * ROOM_GRID_UNIT,
    height: ghostPlacement.value.height * ROOM_GRID_UNIT,
    label: buildRoomFixtureLabel(ghostPlacement.value.type),
  };
});

const previewFloorFixtures = computed(() => {
  return parsedFixtures.value.filter((fixture) => !isWallFixtureType(fixture.type));
});

const previewWallFixtures = computed(() => {
  return parsedFixtures.value.filter((fixture) => isWallFixtureType(fixture.type));
});

function ghostPlacementClass(canPlace: boolean, type: BuilderTool | "seat"): string {
  if (!canPlace) {
    return "border-burgundy bg-burgundy/10 text-burgundy opacity-70";
  }
  if (type === "seat") {
    return "border-navy/70 bg-navy/10";
  }
  return "border-navy/40 bg-white/40";
}

const isValid = computed(() => {
  return name.value.trim().length > 0;
});

async function submit(): Promise<void> {
  if (!isValid.value) {
    return;
  }

  isSubmitting.value = true;
  error.value = null;

  try {
    const payload = {
      name: name.value.trim(),
      grid_cols: roomGrid.value.cols,
      grid_rows: roomGrid.value.rows,
      seats: parsedSeats.value,
      fixtures: parsedFixtures.value,
    };
    const response = isEditing.value && props.template
      ? await apiPut<RoomTemplate>(
          `/api/v1/apps/classroom.group-seating-studio/templates/${props.template.id}`,
          payload,
        )
      : await apiPost<RoomTemplate>(
          "/api/v1/apps/classroom.group-seating-studio/templates",
          payload,
        );
    emit("saved", response);
  } catch (submitError: unknown) {
    error.value = submitError instanceof Error ? submitError.message : "Kunde inte spara klassrummet.";
  } finally {
    isSubmitting.value = false;
  }
}

async function removeTemplate(): Promise<void> {
  if (!props.template) {
    return;
  }

  isDeleting.value = true;
  error.value = null;

  try {
    await apiDelete<void>(`/api/v1/apps/classroom.group-seating-studio/templates/${props.template.id}`);
    emit("deleted", props.template.id);
  } catch (deleteError: unknown) {
    error.value = deleteError instanceof Error ? deleteError.message : "Kunde inte radera klassrummet.";
  } finally {
    isDeleting.value = false;
  }
}
</script>

<template>
  <div class="fixed inset-0 z-50 overflow-y-auto p-4">
    <button
      type="button"
      aria-label="Stäng modal"
      class="fixed inset-0 bg-navy/70"
      @click="emit('close')"
    />
    <div class="relative flex min-h-full items-start justify-center py-4">
      <div class="flex max-h-[calc(100vh-1rem)] w-full max-w-[96vw] flex-col border border-navy bg-white shadow-brutal 2xl:max-w-[1680px]">
        <div class="flex flex-col gap-4 border-b border-navy/20 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div class="space-y-1 px-6 pt-6 md:px-8 md:pt-8">
            <p class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
              Klassrum
            </p>
            <h2 class="font-serif text-2xl text-navy">
              {{ isEditing ? "Redigera klassrum" : "Nytt klassrum" }}
            </h2>
            <p class="max-w-[40rem] text-sm leading-relaxed text-navy/70">
              Placera ut sittplatser och möbler i klassrummet.
            </p>
          </div>
          <button
            type="button"
            class="mb-0 mr-6 mt-6 btn-ghost h-[32px] w-[32px] self-start border-navy/30 bg-canvas px-0 py-0 shadow-none md:mr-8 md:mt-8 lg:self-auto"
            @click="emit('close')"
          >
            ×
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto px-6 pb-6 pt-4 md:px-8 md:pb-8">
          <div
            v-if="error"
            class="system-message system-message-error"
          >
            <div class="system-message-content">
              {{ error }}
            </div>
          </div>

          <div class="mt-6 grid gap-6 xl:grid-cols-[240px_minmax(0,1fr)]">
            <aside class="space-y-5">
              <div class="space-y-1">
                <label class="text-xs font-semibold uppercase tracking-wide text-navy/70">
                  Klassrummets namn
                </label>
                <input
                  v-model="name"
                  type="text"
                  placeholder="Till exempel Sal 304"
                  class="w-full border border-navy bg-white px-3 py-2 text-sm text-navy shadow-brutal-sm"
                >
              </div>

              <div class="border border-navy bg-white p-4 shadow-brutal-sm">
                <div class="mb-3 flex items-end justify-between gap-3">
                  <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                    Storlek
                  </h3>
                  <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                    {{ roomGrid.cols }} × {{ roomGrid.rows }}
                  </span>
                </div>

                <div class="grid gap-3">
                  <div class="flex items-center justify-between gap-3">
                    <span class="text-sm text-navy/70">Bredd</span>
                    <div class="flex items-center gap-2">
                      <button
                        type="button"
                        class="btn-ghost border-navy/30 bg-canvas px-3 py-1 shadow-none disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
                        :disabled="!canShrinkCols"
                        @click="resizeRoom('cols', -1)"
                      >
                        −
                      </button>
                      <button
                        type="button"
                        class="btn-ghost border-navy/30 bg-canvas px-3 py-1 shadow-none"
                        @click="resizeRoom('cols', 1)"
                      >
                        +
                      </button>
                    </div>
                  </div>
                  <div class="flex items-center justify-between gap-3">
                    <span class="text-sm text-navy/70">Höjd</span>
                    <div class="flex items-center gap-2">
                      <button
                        type="button"
                        class="btn-ghost border-navy/30 bg-canvas px-3 py-1 shadow-none disabled:cursor-not-allowed disabled:border-navy/15 disabled:text-navy/35"
                        :disabled="!canShrinkRows"
                        @click="resizeRoom('rows', -1)"
                      >
                        −
                      </button>
                      <button
                        type="button"
                        class="btn-ghost border-navy/30 bg-canvas px-3 py-1 shadow-none"
                        @click="resizeRoom('rows', 1)"
                      >
                        +
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div class="border border-navy bg-canvas p-4 shadow-brutal-sm">
                <div class="mb-3 flex items-end justify-between gap-3">
                  <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                    Verktyg
                  </h3>
                  <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                    {{ parsedSeats.length }} sittplatser
                  </span>
                </div>

                <div class="grid gap-2">
                  <button
                    type="button"
                    class="btn-ghost justify-start shadow-none"
                    :class="selectedTool === 'seat' ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-white'"
                    @click="selectedTool = 'seat'"
                  >
                    Placera plats
                  </button>
                  <button
                    v-for="fixture in roomFixturePalette"
                    :key="fixture.type"
                    type="button"
                    class="btn-ghost justify-start shadow-none"
                    :class="selectedTool === fixture.type ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-white'"
                    @click="selectedTool = fixture.type"
                  >
                    {{ fixture.label }}
                  </button>
                  <button
                    type="button"
                    class="btn-ghost justify-start shadow-none"
                    :class="selectedTool === 'erase' ? 'border-burgundy bg-white text-burgundy' : 'border-navy/30 bg-white'"
                    @click="selectedTool = 'erase'"
                  >
                    Sudda
                  </button>
                  <button
                    type="button"
                    data-test="builder-clear-room"
                    class="btn-ghost justify-start border-navy/30 bg-white text-navy shadow-none"
                    @click="clearRoomContents"
                  >
                    Rensa
                  </button>
                </div>
              </div>

              <div class="border border-navy bg-white p-4 shadow-brutal-sm">
                <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                  Så här gör du
                </h3>
                <p class="mt-2 text-sm leading-relaxed text-navy/70">
                  Välj ett verktyg och för pekaren över rutnätet för att se hur objektet hamnar innan du klickar. Möbler och andra objekt kan inte överlappa sittplatser eller varandra.
                </p>
              </div>
            </aside>

            <section class="flex min-h-0 flex-col gap-4">
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
                      class="btn-ghost border-navy/30 bg-white px-3 py-1 shadow-none"
                      @click="zoomOut"
                    >
                      −
                    </button>
                    <button
                      type="button"
                      data-test="builder-zoom-in"
                      class="btn-ghost border-navy/30 bg-white px-3 py-1 shadow-none"
                      @click="zoomIn"
                    >
                      +
                    </button>
                    <button
                      type="button"
                      data-test="builder-zoom-fit"
                      class="btn-ghost border-navy/30 bg-white px-3 py-1 shadow-none"
                      @click="resetBuilderZoom"
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
                  <div class="flex min-h-full min-w-full items-start justify-center">
                    <div
                      class="relative shrink-0"
                      :style="builderScaledSurfaceStyle"
                    >
                      <div
                        class="absolute left-0 top-0"
                        :style="builderSurfaceTransformStyle"
                        @mouseleave="clearHoverState"
                      >
                        <div
                          class="absolute"
                          :style="roomFloorLayerStyle"
                        >
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
                                class="relative aspect-square border border-navy/20 bg-white text-[9px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] transition-colors hover:border-navy/50"
                                @mousemove="updateHoverState($event, row - 1, col - 1)"
                                @focus="hoveredCell = { row: row - 1, col: col - 1 }"
                                @click="toggleGridCell(row - 1, col - 1, $event)"
                              />
                            </template>

                            <div class="pointer-events-none absolute inset-0 z-10">
                              <div
                                v-for="fixture in builderFloorFixtures"
                                :key="fixture.placement.id"
                                class="absolute overflow-visible"
                                :style="getFloorPlacementStyle(fixture.placement)"
                              >
                                <RoomFixtureArtwork
                                  :fixture="fixture.pixelFixture"
                                  :fixtures="parsedFixtures"
                                  :grid="roomGrid"
                                  surface="builder-grid"
                                />
                              </div>

                              <div
                                v-for="seat in parsedSeats"
                                :key="seat.id"
                                class="absolute"
                                :style="getSeatFrameStyle(seat)"
                              >
                                <RoomSeatToken :seat-id="seat.id" />
                              </div>
                            </div>

                            <div
                              v-if="ghostPlacement && (!ghostRenderableFixture || ghostPlacement.type === 'seat' || !isWallFixtureType(ghostPlacement.type))"
                              class="pointer-events-none absolute inset-0 z-20"
                            >
                              <div
                                v-if="ghostPlacement.type === 'seat'"
                                class="absolute"
                                :style="getSeatGhostFrameStyle(ghostPlacement.row, ghostPlacement.col)"
                              >
                                <RoomSeatToken
                                  :seat-id="`seat-${ghostPlacement.row + 1}-${ghostPlacement.col + 1}`"
                                  ghost
                                />
                              </div>
                              <div
                                v-else-if="ghostRenderableFixture"
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
                          </div>
                        </div>

                        <div
                          class="pointer-events-none absolute inset-0 z-10"
                        >
                          <div
                            v-for="fixture in builderWallFixtures"
                            :key="fixture.placement.id"
                            class="absolute overflow-visible"
                            :style="getWallFixtureFrameStyle(fixture.pixelFixture, roomGrid)"
                          >
                            <RoomFixtureArtwork
                              :fixture="fixture.pixelFixture"
                              :fixtures="parsedFixtures"
                              :grid="roomGrid"
                              surface="builder-grid"
                            />
                          </div>
                        </div>

                        <div
                          v-if="ghostPlacement && ghostPlacement.type !== 'seat' && ghostRenderableFixture && isWallFixtureType(ghostPlacement.type)"
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
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <details class="border border-navy bg-white p-4 shadow-brutal-sm">
                <summary class="flex cursor-pointer list-none flex-wrap items-center justify-between gap-3">
                  <h3 class="text-sm font-semibold uppercase tracking-wide text-navy/70">
                    Förhandsvisning
                  </h3>
                  <span class="text-[11px] font-semibold uppercase tracking-[var(--huleedu-tracking-label)] text-navy/60">
                    {{ parsedSeats.length }} sittplatser
                  </span>
                </summary>

                <div class="relative mt-4 overflow-auto border border-navy/20 bg-canvas p-4">
                  <div
                    class="relative"
                    :style="roomSurfaceStyle"
                  >
                    <div
                      class="absolute opacity-15"
                      :style="{
                        ...roomFloorLayerStyle,
                        backgroundImage: 'linear-gradient(var(--huleedu-navy) 1px, transparent 1px), linear-gradient(90deg, var(--huleedu-navy) 1px, transparent 1px)',
                        backgroundSize: '24px 24px',
                      }"
                    />

                    <div
                      class="absolute"
                      :style="roomFloorLayerStyle"
                    >
                      <div
                        v-for="fixture in previewFloorFixtures"
                        :key="fixture.id"
                        class="absolute overflow-visible"
                        :style="getFloorFixtureFrameStyle(fixture)"
                      >
                        <RoomFixtureArtwork
                          :fixture="fixture"
                          :fixtures="parsedFixtures"
                          :grid="roomGrid"
                        />
                      </div>

                      <div
                        v-for="seat in parsedSeats"
                        :key="seat.id"
                        class="absolute"
                        :style="getSeatFrameStyle(seat)"
                      >
                        <RoomSeatToken :seat-id="seat.id" />
                      </div>
                    </div>

                    <div
                      v-for="fixture in previewWallFixtures"
                      :key="fixture.id"
                      class="absolute overflow-visible"
                      :style="getWallFixtureFrameStyle(fixture, roomGrid)"
                    >
                      <RoomFixtureArtwork
                        :fixture="fixture"
                        :fixtures="parsedFixtures"
                        :grid="roomGrid"
                      />
                    </div>
                  </div>
                </div>
              </details>
            </section>
          </div>
        </div>
        <div class="sticky bottom-0 flex flex-col gap-3 border-t border-navy/20 bg-white px-6 py-4 sm:flex-row sm:items-center sm:justify-between md:px-8">
          <div>
            <button
              v-if="isEditing"
              type="button"
              class="btn-ghost border-burgundy/40 bg-white text-burgundy"
              :disabled="isDeleting"
              @click="removeTemplate"
            >
              {{ isDeleting ? "Raderar..." : "Radera klassrum" }}
            </button>
          </div>
          <div class="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              class="btn-ghost border-navy/30 bg-canvas shadow-none"
              @click="emit('close')"
            >
              Avbryt
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="!isValid || isSubmitting"
              @click="submit"
            >
              {{ isSubmitting ? "Sparar..." : isEditing ? "Spara klassrum" : "Skapa klassrum" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
